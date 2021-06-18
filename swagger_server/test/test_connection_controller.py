# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.connection import Connection  # noqa: E501
from swagger_server.test import BaseTestCase


class TestConnectionController(BaseTestCase):
    """ConnectionController integration test stubs"""

    def test_delete_connection(self):
        """Test case for delete_connection

        Delete connection order by ID
        """
        response = self.client.open(
            '/SDX-Controller/1.0.0/connection/{connectionId}'.format(connection_id=2),
            method='DELETE')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_getconnection_by_id(self):
        """Test case for getconnection_by_id

        Find connection by ID
        """
        response = self.client.open(
            '/SDX-Controller/1.0.0/connection/{connectionId}'.format(connection_id=10),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_place_connection(self):
        """Test case for place_connection

        Place an connection request from the SDX-Controller
        """
        body = Connection()
        response = self.client.open(
            '/SDX-Controller/1.0.0/conection',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
