# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=missing-docstring
# pylint: disable=invalid-name

import unittest

from mock import patch

from citest.gcp_testing import gcp_agent
from citest.base import ExecutionContext

from .test_gcp_agent import (
    FakeGcpDiscovery,
    FakeGcpService,
    TestGcpAgent)


class GcpAgentTest(unittest.TestCase):
  @patch('apiclient.discovery.build')
  def test_download(self, mock_discovery):
    doc = 'HELLO, WORLD!'
    fake_discovery = FakeGcpDiscovery(doc)
    mock_discovery.return_value = fake_discovery
    found = TestGcpAgent.download_discovery_document()
    self.assertEqual(doc, found)
    self.assertEqual(['apis', 'getRest', 'execute'], fake_discovery.calls)

  @patch('apiclient.discovery.build')
  def test_make_agent(self, mock_discovery):
    doc = TestGcpAgent.generate_discovery_document()
    fake_discovery = FakeGcpDiscovery(doc)
    mock_discovery.return_value = fake_discovery
    agent = TestGcpAgent.make_agent()
    self.assertEqual(['apis', 'getRest', 'execute'],
                     fake_discovery.calls)
    self.assertEqual(doc, agent.discovery_document)
    self.assertEqual({}, agent.default_variables)

  def test_resource_method_to_variables_no_defaults(self):
    service = None
    discovery_doc = TestGcpAgent.generate_discovery_document()
    agent = TestGcpAgent(service, discovery_doc)

    got = agent.resource_method_to_variables(
        'get', 'my_test', r='R')
    self.assertEqual({'r': 'R'}, got)

    got = agent.resource_method_to_variables(
        'get', 'my_test', r='R', o='O')
    self.assertEqual({'r': 'R', 'o': 'O'}, got)

    got = agent.resource_method_to_variables(
        'get', 'my_test', resource_id='R')
    self.assertEqual({'r': 'R'}, got)

  def test_resource_method_to_variables_with_defaults(self):
    service = None
    discovery_doc = TestGcpAgent.generate_discovery_document()
    agent = TestGcpAgent(service, discovery_doc,
                         default_variables={'r': 'defR', 'o': 'defO'})
    got = agent.resource_method_to_variables(
        'get', 'my_test', r='R', o='O')
    self.assertEqual({'r': 'R', 'o': 'O'}, got)

    got = agent.resource_method_to_variables(
        'get', 'my_test', r='R')
    self.assertEqual({'r': 'R', 'o': 'defO'}, got)

    got = agent.resource_method_to_variables(
        'get', 'my_test', o='O')
    self.assertEqual({'r': 'defR', 'o': 'O'}, got)

    got = agent.resource_method_to_variables(
        'get', 'my_test')
    self.assertEqual({'r': 'defR', 'o': 'defO'}, got)

    got = agent.resource_method_to_variables(
        'get', 'my_test', o=None)
    self.assertEqual({'r': 'defR'}, got)

  def test_invoke(self):
    context = ExecutionContext()
    doc = TestGcpAgent.generate_discovery_document()
    service = FakeGcpService(['HELLO'])
    agent = TestGcpAgent(service, doc)

    got = agent.invoke_resource(context, 'get', 'my_test', 'MY_ID')
    args = {'r': 'MY_ID'}
    self.assertEqual(['my_test', 'get({0})'.format(args), 'execute'],
                     service.calls)
    self.assertEqual('HELLO', got)

  def test_list(self):
    context = ExecutionContext()
    service = FakeGcpService([{'items': [1, 2, 3]},
                              {'items': [4, 5, 6]}])
    agent = TestGcpAgent.make_test_agent(service=service)

    got = agent.list_resource(context, 'my_test')
    self.assertEqual(['my_test', 'list({})', 'execute',
                      'list_next', 'execute', 'list_next'],
                     service.calls)
    self.assertEqual([1, 2, 3, 4, 5, 6], got)

  def test_resource_type_to_info(self):
    # Verify we can traverse a [nested] discovery document.
    doc = TestGcpAgent.load_discovery_document(
        'container_discovery_document.json')
    service = FakeGcpService([])
    agent = gcp_agent.GcpAgent(service, doc)

    info = agent.resource_type_to_discovery_info('projects.zones.clusters')
    self.assertIsNotNone(info)
    methods = info['methods']
    get = methods['get']
    self.assertEqual(
        'v1/projects/{projectId}/zones/{zone}/clusters/{clusterId}',
        get['path'])

  def test_resource_type_to_variables(self):
    doc = TestGcpAgent.load_discovery_document(
        'container_discovery_document.json')
    service = FakeGcpService([])
    default_vars = {'projectId': 'DEFAULT_PID', 'zone':'MYZONE'}
    agent = gcp_agent.GcpAgent(service, doc, default_variables=default_vars)
    got = agent.resource_method_to_variables('get', 'projects.zones.clusters',
                                             'MYCLUSTER', projectId='MYPID')
    expect = {'projectId': 'MYPID', 'zone': 'MYZONE', 'clusterId': 'MYCLUSTER'}
    self.assertEqual(expect, got)

    got = agent.resource_method_to_variables('get', 'projects.zones.clusters',
                                             clusterId='MYCLUSTER',
                                             projectId='MYPID')
    self.assertEqual(expect, got)

  def test_resource_type_to_variables_missing(self):
    doc = TestGcpAgent.load_discovery_document(
        'container_discovery_document.json')
    service = FakeGcpService([])
    default_vars = {'projectId': 'DEFAULT_PID', 'zone':'MYZONE'}
    agent = gcp_agent.GcpAgent(service, doc, default_variables=default_vars)
    self.assertRaises(ValueError, agent.resource_method_to_variables,
                      'get', 'projects.zones.clusters', projectId='MYPID')


if __name__ == '__main__':
  unittest.main()
