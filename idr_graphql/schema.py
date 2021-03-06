from collections import namedtuple
from itertools import groupby
from operator import itemgetter
import graphene

import omero.clients
from omero.rtypes import unwrap


class AnnotationType(graphene.Enum):
    GENE = 'gene'
    PHENOTYPE = 'phenotype'


class NameValue(graphene.ObjectType):
    name = graphene.String(required=True)
    value = graphene.String(required=True)


class Annotation(graphene.Interface):
    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    images = graphene.List(graphene.NonNull(lambda: Image))
    value = graphene.List(graphene.NonNull(lambda: NameValue))


class MaprAnnotation(graphene.ObjectType):

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    images = graphene.List(graphene.NonNull(lambda: Image))
    value = graphene.List(graphene.NonNull(lambda: NameValue))

    def resolve_images(self, info):
        qs = info.context.get('qs')
        p = omero.sys.ParametersI()
        p.addId(self.id)
        rs = qs.projection(
            """
            SELECT ial.parent.id, ial.parent.name
            FROM ImageAnnotationLink ial
            WHERE ial.child.id=:id
            AND ial.child.class=MapAnnotation
            """, p)
        return (Image(*r) for r in unwrap(rs))


class Gene(MaprAnnotation):
    class Meta:
        interfaces = (Annotation,)


class Phenotype(MaprAnnotation):
    class Meta:
        interfaces = (Annotation,)


class Project(graphene.ObjectType):
    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    datasets = graphene.List(graphene.NonNull(lambda: Dataset))

    def resolve_datasets(self, info):
        qs = info.context.get('qs')
        p = omero.sys.ParametersI()
        p.addId(self.id)
        q = """
            SELECT pdl.child.id, pdl.child.name
            FROM ProjectDatasetLink pdl
            WHERE pdl.parent.id=:id
            ORDER BY id ASC
            """
        rs = qs.projection(q, p)
        return (Dataset(*r) for r in unwrap(rs))


class Dataset(graphene.ObjectType):
    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    projects = graphene.List(graphene.NonNull(lambda: Project))
    images = graphene.List(graphene.NonNull(lambda: Image))

    def resolve_projects(self, info):
        qs = info.context.get('qs')
        p = omero.sys.ParametersI()
        p.addId(self.id)
        q = """
            SELECT pdl.parent.id, pdl.parent.name
            FROM ProjectDatasetLink pdl
            WHERE pdl.child.id=:id
            ORDER BY id ASC
            """
        rs = qs.projection(q, p)
        return (Dataset(*r) for r in unwrap(rs))

    def resolve_images(self, info):
        qs = info.context.get('qs')
        p = omero.sys.ParametersI()
        p.addId(self.id)
        q = """
            SELECT dil.child.id, dil.child.name
            FROM DatasetImageLink dil
            WHERE dil.parent.id=:id
            ORDER BY id ASC
            """
        rs = qs.projection(q, p)
        return (Image(*r) for r in unwrap(rs))


class Image(graphene.ObjectType):
    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    datasets = graphene.List(
        graphene.NonNull(lambda: Dataset))
    annotations = graphene.List(
        graphene.NonNull(lambda: Annotation), mapr=AnnotationType())

    def resolve_datasets(self, info):
        qs = info.context.get('qs')
        p = omero.sys.ParametersI()
        p.addId(self.id)
        q = """
            SELECT dil.parent.id, dil.parent.name
            FROM DatasetImageLink dil
            WHERE dil.child.id=:id
            ORDER BY id ASC
            """
        rs = qs.projection(q, p)
        return (Dataset(*r) for r in unwrap(rs))

    def resolve_annotations(self, info, mapr=None):
        qs = info.context.get('qs')
        p = omero.sys.ParametersI()
        p.addId(self.id)
        nsmap = NSMAP
        if mapr:
            k = 'openmicroscopy.org/mapr/' + mapr
            v = nsmap[k]
            nsmap = {k: v}
        query = []
        for ns, nsd in nsmap.items():
            t = nsd.short
            p.addString(t + 'ns', ns)
            p.addString(t + 'pk', nsd.pk)
            query.append('(ial.child.ns=:{} AND mvq.name=:{})'.format(
                t + 'ns', t + 'pk'))
        q = """
            SELECT ial.child.id, mvq.value, mv.name, mv.value, ial.child.ns
            FROM ImageAnnotationLink ial
            JOIN ial.child.mapValue AS mv
            JOIN ial.child.mapValue AS mvq
            WHERE ial.parent.id=:id
            AND ial.child.class=MapAnnotation
            AND ({})
            ORDER BY ial.child.id ASC
            """.format(' OR '.join(query))
        # print(q)
        rs = qs.projection(q, p)
        return _annFromQueryResultNs(unwrap(rs))


class Query(graphene.ObjectType):
    image = graphene.Field(Image, id=graphene.Int())
    dataset = graphene.Field(Dataset, id=graphene.Int())
    project = graphene.Field(Project, id=graphene.Int())
    gene = graphene.List(Gene, key=graphene.String(), value=graphene.String())

    def resolve_image(self, info, id):
        qs = info.context.get('qs')
        p = omero.sys.ParametersI()
        p.addId(id)
        rs = qs.projection("""
            SELECT id, name
            FROM Image
            WHERE id=:id
            """, p)
        if rs:
            return Image(*unwrap(rs[0]))

    def resolve_dataset(self, info, id):
        qs = info.context.get('qs')
        p = omero.sys.ParametersI()
        p.addId(id)
        rs = qs.projection("""
            SELECT id, name
            FROM Dataset
            WHERE id=:id
            """, p)
        if rs:
            return Dataset(*unwrap(rs[0]))

    def resolve_project(self, info, id):
        qs = info.context.get('qs')
        p = omero.sys.ParametersI()
        p.addId(id)
        rs = qs.projection("""
            SELECT id, name
            FROM Project
            WHERE id=:id
            """, p)
        if rs:
            return Project(*unwrap(rs[0]))


    def resolve_gene(self, info, key, value):
        qs = info.context.get('qs')
        p = omero.sys.ParametersI()
        p.page(0, 10)
        p.addString('key', key)
        p.addString('value', value)
        rs = qs.projection("""
            SELECT ann.id, mvq.value, mv.name, mv.value
            FROM MapAnnotation ann
            JOIN ann.mapValue AS mv
            JOIN ann.mapValue AS mvq
            WHERE ann.ns='openmicroscopy.org/mapr/gene'
            AND mvq.name=:key
            AND lower(mvq.value)=:value
            ORDER BY ann.id ASC
            """, p)
        return _annFromQueryResult(unwrap(rs), Gene)


NsDetails = namedtuple('NsDetails', ['short', 'cls', 'pk'])
NSMAP = {
    'openmicroscopy.org/mapr/gene': NsDetails(
        'ge', Gene, 'Gene Symbol'),
    'openmicroscopy.org/mapr/phenotype': NsDetails(
        'ph', Phenotype, 'Phenotype'),
}


def _annFromQueryResult(rs, AnnClass):
    for k, g in groupby(rs, itemgetter(0, 1)):
        id = k[0]
        name = k[1]
        nvs = [NameValue(el[2], el[3]) for el in g]
        ann = AnnClass(id=id, name=name, value=nvs)
        yield ann


def _annFromQueryResultNs(rs):
    for k, g in groupby(rs, itemgetter(0, 1, 4)):
        id = k[0]
        name = k[1]
        ns = k[2]
        nvs = [NameValue(el[2], el[3]) for el in g]
        annClass = NSMAP[ns].cls
        ann = annClass(id=id, name=name, value=nvs)
        yield ann


schema = graphene.Schema(query=Query, types=(Gene, Phenotype))
