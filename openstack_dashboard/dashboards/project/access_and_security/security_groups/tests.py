# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import cgi

from django.conf import settings
from django.core.urlresolvers import reverse
from django import http

from mox import IsA  # noqa

from openstack_dashboard import api
from openstack_dashboard.test import helpers as test

from openstack_dashboard.dashboards.project.access_and_security.\
    security_groups import tables


INDEX_URL = reverse('horizon:project:access_and_security:index')
SG_CREATE_URL = reverse('horizon:project:access_and_security:'
                        'security_groups:create')


def strip_absolute_base(uri):
    return uri.split(settings.TESTSERVER, 1)[-1]


class SecurityGroupsViewTests(test.TestCase):
    secgroup_backend = 'nova'

    def setUp(self):
        super(SecurityGroupsViewTests, self).setUp()
        sec_group = self.security_groups.first()
        self.detail_url = reverse('horizon:project:access_and_security:'
                                  'security_groups:detail',
                                  args=[sec_group.id])
        self.edit_url = reverse('horizon:project:access_and_security:'
                                'security_groups:add_rule',
                                args=[sec_group.id])

    @test.create_stubs({api.network: ('security_group_rule_create',
                                      'security_group_list',
                                      'security_group_backend')})
    def _add_security_group_rule_fixture(self, **kwargs):
        sec_group = self.security_groups.first()
        sec_group_list = self.security_groups.list()
        rule = self.security_group_rules.first()

        api.network.security_group_backend(
            IsA(http.HttpRequest)).AndReturn(self.secgroup_backend)
        api.network.security_group_rule_create(
            IsA(http.HttpRequest),
            kwargs.get('sec_group', sec_group.id),
            kwargs.get('ingress', 'ingress'),
            kwargs.get('ethertype', 'IPv4'),
            kwargs.get('ip_protocol', rule.ip_protocol),
            kwargs.get('from_port', int(rule.from_port)),
            kwargs.get('to_port', int(rule.to_port)),
            kwargs.get('cidr', rule.ip_range['cidr']),
            kwargs.get('security_group', u'%s' % sec_group.id)).AndReturn(rule)
        api.network.security_group_list(
            IsA(http.HttpRequest)).AndReturn(sec_group_list)
        return sec_group, rule

    @test.create_stubs({api.network: ('security_group_get',)})
    def test_update_security_groups_get(self):
        sec_group = self.security_groups.first()
        api.network.security_group_get(IsA(http.HttpRequest),
                                        sec_group.id).AndReturn(sec_group)
        self.mox.ReplayAll()

        res = self.client.get(reverse('horizon:project:access_and_security:'
                                      'security_groups:update',
                                      args=[sec_group.id]))
        self.assertTemplateUsed(res,
                'project/access_and_security/security_groups/_update.html')
        self.assertEqual(res.context['security_group'].name,
                         sec_group.name)

    @test.create_stubs({api.network: ('security_group_update',
                                      'security_group_get')})
    def test_update_security_groups_post(self):
        sec_group = self.security_groups.get(name="other_group")
        api.network.security_group_update(IsA(http.HttpRequest),
                                       str(sec_group.id),
                                       sec_group.name,
                                       sec_group.description) \
            .AndReturn(sec_group)
        api.network.security_group_get(IsA(http.HttpRequest),
                                        sec_group.id).AndReturn(sec_group)
        self.mox.ReplayAll()

        formData = {'method': 'UpdateGroup',
                    'id': sec_group.id,
                    'name': sec_group.name,
                    'description': sec_group.description}

        update_url = reverse('horizon:project:access_and_security:'
                             'security_groups:update',
                             args=[sec_group.id])
        res = self.client.post(update_url, formData)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    def test_create_security_groups_get(self):
        res = self.client.get(SG_CREATE_URL)
        self.assertTemplateUsed(res,
                    'project/access_and_security/security_groups/create.html')

    @test.create_stubs({api.network: ('security_group_create',)})
    def test_create_security_groups_post(self):
        sec_group = self.security_groups.first()
        api.network.security_group_create(IsA(http.HttpRequest),
                                       sec_group.name,
                                       sec_group.description) \
            .AndReturn(sec_group)
        self.mox.ReplayAll()

        formData = {'method': 'CreateGroup',
                    'name': sec_group.name,
                    'description': sec_group.description}
        res = self.client.post(SG_CREATE_URL, formData)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({api.network: ('security_group_create',)})
    def test_create_security_groups_post_exception(self):
        sec_group = self.security_groups.first()
        api.network.security_group_create(IsA(http.HttpRequest),
                                       sec_group.name,
                                       sec_group.description) \
            .AndRaise(self.exceptions.nova)
        self.mox.ReplayAll()

        formData = {'method': 'CreateGroup',
                    'name': sec_group.name,
                    'description': sec_group.description}
        res = self.client.post(SG_CREATE_URL, formData)
        self.assertMessageCount(error=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({api.network: ('security_group_create',)})
    def test_create_security_groups_post_wrong_name(self):
        sec_group = self.security_groups.first()
        fail_name = sec_group.name + ' invalid'
        self.mox.ReplayAll()

        formData = {'method': 'CreateGroup',
                    'name': fail_name,
                    'description': sec_group.description}
        res = self.client.post(SG_CREATE_URL, formData)
        self.assertTemplateUsed(res,
                    'project/access_and_security/security_groups/create.html')
        self.assertContains(res, "ASCII")

    @test.create_stubs({api.network: ('security_group_get',)})
    def test_detail_get(self):
        sec_group = self.security_groups.first()

        api.network.security_group_get(IsA(http.HttpRequest),
                                       sec_group.id).AndReturn(sec_group)
        self.mox.ReplayAll()
        res = self.client.get(self.detail_url)
        self.assertTemplateUsed(res,
                'project/access_and_security/security_groups/detail.html')

    @test.create_stubs({api.network: ('security_group_get',)})
    def test_detail_get_exception(self):
        sec_group = self.security_groups.first()

        api.network.security_group_get(IsA(http.HttpRequest),
                                    sec_group.id) \
                .AndRaise(self.exceptions.nova)

        self.mox.ReplayAll()

        res = self.client.get(self.detail_url)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    def test_detail_add_rule_cidr(self):
        sec_group, rule = self._add_security_group_rule_fixture(
            security_group=None)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'port',
                    'port': rule.from_port,
                    'rule_menu': rule.ip_protocol,
                    'cidr': rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertRedirectsNoFollow(res, self.detail_url)

    def test_detail_add_rule_cidr_with_invalid_unused_fields(self):
        sec_group, rule = self._add_security_group_rule_fixture(
            security_group=None)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'port',
                    'port': rule.from_port,
                    'to_port': 'INVALID',
                    'from_port': 'INVALID',
                    'icmp_code': 'INVALID',
                    'icmp_type': 'INVALID',
                    'security_group': 'INVALID',
                    'ip_protocol': 'INVALID',
                    'rule_menu': rule.ip_protocol,
                    'cidr': rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, self.detail_url)

    def test_detail_add_rule_securitygroup_with_invalid_unused_fields(self):
        sec_group, rule = self._add_security_group_rule_fixture(
            cidr=None, ethertype='')
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'port',
                    'port': rule.from_port,
                    'to_port': 'INVALID',
                    'from_port': 'INVALID',
                    'icmp_code': 'INVALID',
                    'icmp_type': 'INVALID',
                    'security_group': sec_group.id,
                    'ip_protocol': 'INVALID',
                    'rule_menu': rule.ip_protocol,
                    'cidr': 'INVALID',
                    'remote': 'sg'}
        res = self.client.post(self.edit_url, formData)
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, self.detail_url)

    def test_detail_add_rule_icmp_with_invalid_unused_fields(self):
        sec_group, rule = self._add_security_group_rule_fixture(
            ip_protocol='icmp', security_group=None)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'port',
                    'port': 'INVALID',
                    'to_port': 'INVALID',
                    'from_port': 'INVALID',
                    'icmp_code': rule.to_port,
                    'icmp_type': rule.from_port,
                    'security_group': sec_group.id,
                    'ip_protocol': 'INVALID',
                    'rule_menu': 'icmp',
                    'cidr': rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertNoFormErrors(res)
        self.assertRedirectsNoFollow(res, self.detail_url)

    @test.create_stubs({api.network: ('security_group_rule_create',
                                      'security_group_list',
                                      'security_group_backend')})
    def test_detail_add_rule_cidr_with_template(self):
        sec_group = self.security_groups.first()
        sec_group_list = self.security_groups.list()
        rule = self.security_group_rules.first()

        api.network.security_group_backend(
            IsA(http.HttpRequest)).AndReturn(self.secgroup_backend)
        api.network.security_group_rule_create(IsA(http.HttpRequest),
                                               sec_group.id,
                                               'ingress', 'IPv4',
                                               rule.ip_protocol,
                                               int(rule.from_port),
                                               int(rule.to_port),
                                               rule.ip_range['cidr'],
                                               None).AndReturn(rule)
        api.network.security_group_list(
            IsA(http.HttpRequest)).AndReturn(sec_group_list)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'rule_menu': 'http',
                    'port_or_range': 'port',
                    'cidr': rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertRedirectsNoFollow(res, self.detail_url)

    def _get_source_group_rule(self):
        return self.security_group_rules.get(id=3)

    @test.create_stubs({api.network: ('security_group_rule_create',
                                      'security_group_list',
                                      'security_group_backend')})
    def test_detail_add_rule_self_as_source_group(self):
        sec_group = self.security_groups.first()
        sec_group_list = self.security_groups.list()
        rule = self._get_source_group_rule()

        api.network.security_group_backend(
            IsA(http.HttpRequest)).AndReturn(self.secgroup_backend)
        api.network.security_group_rule_create(
            IsA(http.HttpRequest),
            sec_group.id,
            'ingress',
            # ethertype is empty for source_group of Nova Security Group
            '',
            rule.ip_protocol,
            int(rule.from_port),
            int(rule.to_port),
            None,
            u'%s' % sec_group.id).AndReturn(rule)
        api.network.security_group_list(
            IsA(http.HttpRequest)).AndReturn(sec_group_list)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'port',
                    'port': rule.from_port,
                    'rule_menu': rule.ip_protocol,
                    'cidr': '0.0.0.0/0',
                    'security_group': sec_group.id,
                    'remote': 'sg'}
        res = self.client.post(self.edit_url, formData)
        self.assertRedirectsNoFollow(res, self.detail_url)

    @test.create_stubs({api.network: ('security_group_rule_create',
                                      'security_group_list',
                                      'security_group_backend')})
    def test_detail_add_rule_self_as_source_group_with_template(self):
        sec_group = self.security_groups.first()
        sec_group_list = self.security_groups.list()
        rule = self._get_source_group_rule()

        api.network.security_group_backend(
            IsA(http.HttpRequest)).AndReturn(self.secgroup_backend)
        api.network.security_group_rule_create(
            IsA(http.HttpRequest),
            sec_group.id,
            'ingress',
            # ethertype is empty for source_group of Nova Security Group
            '',
            rule.ip_protocol,
            int(rule.from_port),
            int(rule.to_port),
            None,
            u'%s' % sec_group.id).AndReturn(rule)
        api.network.security_group_list(
            IsA(http.HttpRequest)).AndReturn(sec_group_list)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'rule_menu': 'http',
                    'port_or_range': 'port',
                    'cidr': '0.0.0.0/0',
                    'security_group': sec_group.id,
                    'remote': 'sg'}
        res = self.client.post(self.edit_url, formData)
        self.assertRedirectsNoFollow(res, self.detail_url)

    @test.create_stubs({api.network: ('security_group_list',
                                      'security_group_backend')})
    def test_detail_invalid_port(self):
        sec_group = self.security_groups.first()
        sec_group_list = self.security_groups.list()
        rule = self.security_group_rules.first()

        api.network.security_group_backend(
            IsA(http.HttpRequest)).AndReturn(self.secgroup_backend)
        api.network.security_group_list(
            IsA(http.HttpRequest)).AndReturn(sec_group_list)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'port',
                    'port': None,
                    'rule_menu': rule.ip_protocol,
                    'cidr': rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertNoMessages()
        self.assertContains(res, "The specified port is invalid")

    @test.create_stubs({api.network: ('security_group_list',
                                      'security_group_backend')})
    def test_detail_invalid_port_range(self):
        sec_group = self.security_groups.first()
        sec_group_list = self.security_groups.list()
        rule = self.security_group_rules.first()

        for i in range(3):
            api.network.security_group_backend(
                IsA(http.HttpRequest)).AndReturn(self.secgroup_backend)
            api.network.security_group_list(
                IsA(http.HttpRequest)).AndReturn(sec_group_list)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'range',
                    'from_port': rule.from_port,
                    'to_port': int(rule.from_port) - 1,
                    'rule_menu': rule.ip_protocol,
                    'cidr': rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertNoMessages()
        self.assertContains(res, "greater than or equal to")

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'range',
                    'from_port': None,
                    'to_port': rule.to_port,
                    'rule_menu': rule.ip_protocol,
                    'cidr': rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertNoMessages()
        self.assertContains(res, cgi.escape('"from" port number is invalid',
                                            quote=True))

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'range',
                    'from_port': rule.from_port,
                    'to_port': None,
                    'rule_menu': rule.ip_protocol,
                    'cidr': rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertNoMessages()
        self.assertContains(res, cgi.escape('"to" port number is invalid',
                                            quote=True))

    @test.create_stubs({api.network: ('security_group_get',
                                      'security_group_list',
                                      'security_group_backend')})
    def test_detail_invalid_icmp_rule(self):
        sec_group = self.security_groups.first()
        sec_group_list = self.security_groups.list()
        icmp_rule = self.security_group_rules.list()[1]

        # Call POST 4 times
        for i in range(4):
            api.network.security_group_backend(
                IsA(http.HttpRequest)).AndReturn(self.secgroup_backend)
            api.network.security_group_list(
                IsA(http.HttpRequest)).AndReturn(sec_group_list)

        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'port',
                    'icmp_type': 256,
                    'icmp_code': icmp_rule.to_port,
                    'rule_menu': icmp_rule.ip_protocol,
                    'cidr': icmp_rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertNoMessages()
        self.assertContains(res, "The ICMP type not in range (-1, 255)")

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'port',
                    'icmp_type': icmp_rule.from_port,
                    'icmp_code': 256,
                    'rule_menu': icmp_rule.ip_protocol,
                    'cidr': icmp_rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertNoMessages()
        self.assertContains(res, "The ICMP code not in range (-1, 255)")

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'port',
                    'icmp_type': icmp_rule.from_port,
                    'icmp_code': None,
                    'rule_menu': icmp_rule.ip_protocol,
                    'cidr': icmp_rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertNoMessages()
        self.assertContains(res, "The ICMP code is invalid")

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'port',
                    'icmp_type': None,
                    'icmp_code': icmp_rule.to_port,
                    'rule_menu': icmp_rule.ip_protocol,
                    'cidr': icmp_rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertNoMessages()
        self.assertContains(res, "The ICMP type is invalid")

    @test.create_stubs({api.network: ('security_group_rule_create',
                                      'security_group_list',
                                      'security_group_backend')})
    def test_detail_add_rule_exception(self):
        sec_group = self.security_groups.first()
        sec_group_list = self.security_groups.list()
        rule = self.security_group_rules.first()

        api.network.security_group_backend(
            IsA(http.HttpRequest)).AndReturn(self.secgroup_backend)
        api.network.security_group_rule_create(
            IsA(http.HttpRequest),
            sec_group.id, 'ingress', 'IPv4',
            rule.ip_protocol,
            int(rule.from_port),
            int(rule.to_port),
            rule.ip_range['cidr'],
            None).AndRaise(self.exceptions.nova)
        api.network.security_group_list(
            IsA(http.HttpRequest)).AndReturn(sec_group_list)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'port_or_range': 'port',
                    'port': rule.from_port,
                    'rule_menu': rule.ip_protocol,
                    'cidr': rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertRedirectsNoFollow(res, self.detail_url)

    @test.create_stubs({api.network: ('security_group_rule_delete',)})
    def test_detail_delete_rule(self):
        sec_group = self.security_groups.first()
        rule = self.security_group_rules.first()

        api.network.security_group_rule_delete(IsA(http.HttpRequest), rule.id)
        self.mox.ReplayAll()

        form_data = {"action": "rules__delete__%s" % rule.id}
        req = self.factory.post(self.edit_url, form_data)
        kwargs = {'security_group_id': sec_group.id}
        table = tables.RulesTable(req, sec_group.rules, **kwargs)
        handled = table.maybe_handle()
        self.assertEqual(strip_absolute_base(handled['location']),
                         self.detail_url)

    @test.create_stubs({api.network: ('security_group_rule_delete',)})
    def test_detail_delete_rule_exception(self):
        sec_group = self.security_groups.first()
        rule = self.security_group_rules.first()

        api.network.security_group_rule_delete(
            IsA(http.HttpRequest),
            rule.id).AndRaise(self.exceptions.nova)
        self.mox.ReplayAll()

        form_data = {"action": "rules__delete__%s" % rule.id}
        req = self.factory.post(self.edit_url, form_data)
        kwargs = {'security_group_id': sec_group.id}
        table = tables.RulesTable(
            req, self.security_group_rules.list(), **kwargs)
        handled = table.maybe_handle()
        self.assertEqual(strip_absolute_base(handled['location']),
                         self.detail_url)

    @test.create_stubs({api.network: ('security_group_delete',)})
    def test_delete_group(self):
        sec_group = self.security_groups.get(name="other_group")

        api.network.security_group_delete(IsA(http.HttpRequest), sec_group.id)
        self.mox.ReplayAll()

        form_data = {"action": "security_groups__delete__%s" % sec_group.id}
        req = self.factory.post(INDEX_URL, form_data)
        table = tables.SecurityGroupsTable(req, self.security_groups.list())
        handled = table.maybe_handle()
        self.assertEqual(strip_absolute_base(handled['location']),
                         INDEX_URL)

    @test.create_stubs({api.network: ('security_group_delete',)})
    def test_delete_group_exception(self):
        sec_group = self.security_groups.get(name="other_group")

        api.network.security_group_delete(
            IsA(http.HttpRequest),
            sec_group.id).AndRaise(self.exceptions.nova)

        self.mox.ReplayAll()

        form_data = {"action": "security_groups__delete__%s" % sec_group.id}
        req = self.factory.post(INDEX_URL, form_data)
        table = tables.SecurityGroupsTable(req, self.security_groups.list())
        handled = table.maybe_handle()

        self.assertEqual(strip_absolute_base(handled['location']),
                         INDEX_URL)


class SecurityGroupsNovaNeutronDriverTests(SecurityGroupsViewTests):
    secgroup_backend = 'nova'

    def setUp(self):
        super(SecurityGroupsNovaNeutronDriverTests, self).setUp()

        self._sec_groups_orig = self.security_groups
        self.security_groups = self.security_groups_uuid

        self._sec_group_rules_orig = self.security_group_rules
        self.security_group_rules = self.security_group_rules_uuid

        sec_group = self.security_groups.first()
        self.detail_url = reverse('horizon:project:access_and_security:'
                                  'security_groups:detail',
                                  args=[sec_group.id])
        self.edit_url = reverse('horizon:project:access_and_security:'
                                'security_groups:add_rule',
                                args=[sec_group.id])

    def tearDown(self):
        self.security_groups = self._sec_groups_orig
        self.security_group_rules = self._sec_group_rules_orig
        super(SecurityGroupsNovaNeutronDriverTests, self).tearDown()


class SecurityGroupsNeutronTests(SecurityGroupsViewTests):
    secgroup_backend = 'neutron'

    def setUp(self):
        super(SecurityGroupsNeutronTests, self).setUp()

        self._sec_groups_orig = self.security_groups
        self.security_groups = self.q_secgroups

        self._sec_group_rules_orig = self.security_group_rules
        self.security_group_rules = self.q_secgroup_rules

        sec_group = self.security_groups.first()
        self.detail_url = reverse('horizon:project:access_and_security:'
                                  'security_groups:detail',
                                  args=[sec_group.id])
        self.edit_url = reverse('horizon:project:access_and_security:'
                                'security_groups:add_rule',
                                args=[sec_group.id])

    def tearDown(self):
        self.security_groups = self._sec_groups_orig
        self.security_group_rules = self._sec_group_rules_orig
        super(SecurityGroupsNeutronTests, self).tearDown()

    def _get_source_group_rule(self):
        for rule in self.security_group_rules.list():
            if rule.group:
                return rule
        raise Exception("No matches found.")

    # Additional tests for Neutron Security Group original features

    @test.create_stubs({api.network: ('security_group_rule_create',
                                      'security_group_list',
                                      'security_group_backend')})
    def test_detail_add_rule_custom_protocol(self):
        sec_group = self.security_groups.first()
        sec_group_list = self.security_groups.list()
        rule = self.security_group_rules.first()

        api.network.security_group_backend(
            IsA(http.HttpRequest)).AndReturn(self.secgroup_backend)
        api.network.security_group_rule_create(IsA(http.HttpRequest),
                                               sec_group.id, 'ingress', 'IPv6',
                                               37, None, None, 'fe80::/48',
                                               None).AndReturn(rule)
        api.network.security_group_list(
            IsA(http.HttpRequest)).AndReturn(sec_group_list)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'rule_menu': 'custom',
                    'direction': 'ingress',
                    'port_or_range': 'port',
                    'ip_protocol': 37,
                    'cidr': 'fe80::/48',
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertRedirectsNoFollow(res, self.detail_url)

    @test.create_stubs({api.network: ('security_group_rule_create',
                                      'security_group_list',
                                      'security_group_backend')})
    def test_detail_add_rule_egress(self):
        sec_group = self.security_groups.first()
        sec_group_list = self.security_groups.list()
        rule = self.security_group_rules.first()

        api.network.security_group_backend(
            IsA(http.HttpRequest)).AndReturn(self.secgroup_backend)
        api.network.security_group_rule_create(IsA(http.HttpRequest),
                                               sec_group.id, 'egress', 'IPv4',
                                               'udp', 80, 80, '10.1.1.0/24',
                                               None).AndReturn(rule)
        api.network.security_group_list(
            IsA(http.HttpRequest)).AndReturn(sec_group_list)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'direction': 'egress',
                    'rule_menu': 'udp',
                    'port_or_range': 'port',
                    'port': 80,
                    'cidr': '10.1.1.0/24',
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertRedirectsNoFollow(res, self.detail_url)

    @test.create_stubs({api.network: ('security_group_rule_create',
                                      'security_group_list',
                                      'security_group_backend')})
    def test_detail_add_rule_egress_with_all_tcp(self):
        sec_group = self.security_groups.first()
        sec_group_list = self.security_groups.list()
        rule = self.security_group_rules.list()[3]

        api.network.security_group_backend(
            IsA(http.HttpRequest)).AndReturn(self.secgroup_backend)
        api.network.security_group_rule_create(IsA(http.HttpRequest),
                                               sec_group.id, 'egress', 'IPv4',
                                               rule.ip_protocol,
                                               int(rule.from_port),
                                               int(rule.to_port),
                                               rule.ip_range['cidr'],
                                               None).AndReturn(rule)
        api.network.security_group_list(
            IsA(http.HttpRequest)).AndReturn(sec_group_list)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'direction': 'egress',
                    'port_or_range': 'range',
                    'rule_menu': 'all_tcp',
                    'cidr': rule.ip_range['cidr'],
                    'remote': 'cidr'}
        res = self.client.post(self.edit_url, formData)
        self.assertRedirectsNoFollow(res, self.detail_url)

    @test.create_stubs({api.network: ('security_group_rule_create',
                                      'security_group_list',
                                      'security_group_backend')})
    def test_detail_add_rule_source_group_with_direction_ethertype(self):
        sec_group = self.security_groups.first()
        sec_group_list = self.security_groups.list()
        rule = self._get_source_group_rule()

        api.network.security_group_backend(
            IsA(http.HttpRequest)).AndReturn(self.secgroup_backend)
        api.network.security_group_rule_create(
            IsA(http.HttpRequest),
            sec_group.id,
            'egress',
            # ethertype is empty for source_group of Nova Security Group
            'IPv6',
            rule.ip_protocol,
            int(rule.from_port),
            int(rule.to_port),
            None,
            u'%s' % sec_group.id).AndReturn(rule)
        api.network.security_group_list(
            IsA(http.HttpRequest)).AndReturn(sec_group_list)
        self.mox.ReplayAll()

        formData = {'method': 'AddRule',
                    'id': sec_group.id,
                    'direction': 'egress',
                    'port_or_range': 'port',
                    'port': rule.from_port,
                    'rule_menu': rule.ip_protocol,
                    'cidr': '0.0.0.0/0',
                    'security_group': sec_group.id,
                    'remote': 'sg',
                    'ethertype': 'IPv6'}
        res = self.client.post(self.edit_url, formData)
        self.assertRedirectsNoFollow(res, self.detail_url)
