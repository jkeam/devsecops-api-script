#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause

from devsecops.base.base_handler import BaseApiHandler, UnexpectedApiResponse
from typing import TypeVar
from base64 import b64encode
import requests
import json

T = TypeVar("T", bound="Nexus")


class Nexus(BaseApiHandler):
    def __init__(self, base_url: str = None, username: str = None,
                 password: str = None, verbosity: int = 0) -> None:
        """
        Initialize a Nexus API wrapper with logging, url information, and other
        necessary variables to track state.
        """
        super().__init__(
            service_name='Nexus',
            base_url=base_url,
            base_endpoint='service/rest',
            username=username,
            password=password,
            verbosity=verbosity,
            auth=True
        )
        self.base_url = base_url

    def sign_in(self) -> None:
        """
        Sign in to a Nexus API instance with appropriate encoding
        """
        self._get_session()

        b64_username = b64encode(self.username.encode('utf-8'))
        b64_password = b64encode(self.password.encode('utf-8'))
        login_data = {
            'u': b64_username.decode('ascii'),
            'p': b64_password.decode('ascii')
        }
        token = json.loads(self.api_req('post', 'wonderland/authenticate',
                                        data=login_data).text).get('t')
        self.session.headers.update({'X-NX-AuthTicket': token})

    def sign_out(self) -> None:
        """
        Just close the Nexus API session
        """
        self.session.close()

    def add_user(self, username: str = None,
                 password: str = None, roles: list = []) -> requests.Response:
        """
        Add a user to the Nexus instance, returning None if no user was created
        """
        data = {
            'userId': username,
            'firstName': username,
            'lastName': username,
            'password': password,
            'emailAddress': f'{username}@example.com',
            'status': 'active',
            'roles': roles
        }
        try:
            return self.api_req('post', 'beta/security/users', data)
        except UnexpectedApiResponse as e:
            self.logger.error(f'Error adding {username}')
            self.logger.info(json.loads(str(e)).get('error_message'))
            pass

    def list_users(self) -> list:
        """
        Lists all users currently on the server
        """
        return json.loads(self.api_req(endpoint='beta/security/users').text)

    def search_users(self, username: str = None) -> list:
        """
        Returns information about the queried users as a list of results
        """
        return json.loads(
            self.api_req('get', f'beta/security/users?userId={username}').text
        )

    def change_password(self, username: str = None,
                        password: str = None) -> requests.Response:
        """
        Changes the password for a given username to the provided password
        """
        self.session.headers.update({'Content-type': 'text/plain'})
        ret_val =  self.session.put(
            f'{self.url}/beta/security/users/{username}/change-password',
            data=password
        )
        self.session.headers.update({'Content-type': 'application/json'})
        return ret_val

    def list_repos(self) -> list:
        """
        Returns a list of all repositories configured on the server
        """
        return json.loads(
            self.api_req('get', 'beta/repositories').text
        )

    def add_repo(self, reponame: str = None) -> requests.Response:
        """
        Adds a Maven2 format release repository backed by the default blobstore
        to the server.
        """
        data = {
            'name': reponame,
            'online': True,
            'format': 'maven2',
            'storage': {
                'blobStoreName': 'default',
                'strictContentTypeValidation': True,
                'writePolicy': 'ALLOW_ONCE'
            },
            'type': 'hosted',
            'cleanup': None,
            'maven': {
                'versionPolicy': 'RELEASE',
                'layoutPolicy': 'STRICT'
            }
        }
        return self.api_req('post', 'beta/repositories/maven/hosted', data,
                            ok=201)

    def search_repos(self, reponame: str = '') -> list:
        """
        Returns a list of all repositories whose name is similar to reponame
        on the server.
        """
        def is_similar_to(repo: dict = {}, reponame: str = reponame) -> bool:
            return repo.get('name', '').startswith(reponame) or \
                   repo.get('name', '').endswith(reponame) or \
                   reponame in repo.get('name', '')

        return list(filter(is_similar_to, self.list_repos()))
