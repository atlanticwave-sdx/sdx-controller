# coding: utf-8

from __future__ import absolute_import

from flask import json

from sdx_controller.models.user import User  # noqa: E501
from sdx_controller.test import BaseTestCase


class TestUserController(BaseTestCase):
    """UserController integration test stubs"""

    def test_create_user(self):
        """Test case for create_user

        Create user
        """
        body = User()
        response = self.client.open(
            "/SDX-Controller/user",
            method="POST",
            data=json.dumps(body),
            content_type="application/json",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_create_users_with_array_input(self):
        """Test case for create_users_with_array_input

        Creates list of users with given input array
        """
        body = [User()]
        response = self.client.open(
            "/SDX-Controller/user/createWithArray",
            method="POST",
            data=json.dumps(body),
            content_type="application/json",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_create_users_with_list_input(self):
        """Test case for create_users_with_list_input

        Creates list of users with given input array
        """
        body = [User()]
        response = self.client.open(
            "/SDX-Controller/user/createWithList",
            method="POST",
            data=json.dumps(body),
            content_type="application/json",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_delete_user(self):
        """Test case for delete_user

        Delete user
        """
        response = self.client.open(
            "/SDX-Controller/user/{username}".format(username="username_example"),
            method="DELETE",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_get_user_by_name(self):
        """Test case for get_user_by_name

        Get user by user name
        """
        response = self.client.open(
            "/SDX-Controller/user/{username}".format(username="username_example"),
            method="GET",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_login_user(self):
        """Test case for login_user

        Logs user into the system
        """
        query_string = [
            ("username", "username_example"),
            ("password", "password_example"),
        ]
        response = self.client.open(
            "/SDX-Controller/user/login", method="GET", query_string=query_string
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_logout_user(self):
        """Test case for logout_user

        Logs out current logged in user session
        """
        response = self.client.open("/SDX-Controller/user/logout", method="GET")
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))

    def test_update_user(self):
        """Test case for update_user

        Updated user
        """
        body = User()
        response = self.client.open(
            "/SDX-Controller/user/{username}".format(username="username_example"),
            method="PUT",
            data=json.dumps(body),
            content_type="application/json",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))


if __name__ == "__main__":
    import unittest

    unittest.main()
