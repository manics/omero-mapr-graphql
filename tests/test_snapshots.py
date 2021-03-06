from graphene.test import Client
from idr_graphql import schema

# These tests will create a snapshot dir and a snapshot file the first
# time the test is executed, with the response of the execution.


def test_image_gene(omero, snapshot):
    client = Client(schema)
    snapshot.assert_match(client.execute("""{
      image(id: 1030631) {
        id
        name
        annotations(mapr: GENE) {
          __typename
          name
        }
      }
    }""", context=omero))


def test_image_phenotype(omero, snapshot):
    client = Client(schema)
    snapshot.assert_match(client.execute("""{
      image(id: 1030631) {
        id
        name
        annotations(mapr: PHENOTYPE) {
          __typename
          name
        }
      }
    }""", context=omero))


def test_project(omero, snapshot):
    client = Client(schema)
    snapshot.assert_match(client.execute("""{
      project(id: 151) {
        id
        name
        datasets {
          id
          name
        }
      }
    }""", context=omero))


def test_dataset(omero, snapshot):
    client = Client(schema)
    snapshot.assert_match(client.execute("""{
      dataset(id: 369) {
        id
        name
        images {
          id
          name
        }
        projects {
          id
          name
        }
      }
    }""", context=omero))


def test_image_dataset(omero, snapshot):
    client = Client(schema)
    snapshot.assert_match(client.execute("""{
      image(id: 1920095) {
        id
        name
        datasets {
          id
          name
        }
      }
    }""", context=omero))


def test_gene(omero, snapshot):
    client = Client(schema)
    snapshot.assert_match(client.execute("""{
      gene(key: "Gene Symbol", value: "djc5b") {
        id
        name
        images {
          id
          name
        }
      }
    }""", context=omero))
