# Copyright 2015-2016 Yelp Inc.
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
from behave import then
from pyramid import testing

from paasta_tools.api import settings
from paasta_tools.api.views.instance import instance_status
from paasta_tools.utils import decompose_job_id
from paasta_tools.utils import load_system_paasta_config


@then(u'instance GET should return status "{status}" and "{marathon_status}" for "{job_id}"')
def service_instance_status(context, status, marathon_status, job_id):
    settings.cluster = load_system_paasta_config().get_cluster()
    settings.soa_dir = context.soa_dir

    (service, instance, _, __) = decompose_job_id(job_id)

    request = testing.DummyRequest()
    request.matchdict = {'service': service, 'instance': instance}
    response = instance_status(request)

    assert response['state'] == status
    assert response['marathon']['status'] == marathon_status


@then(u'instance GET should return error code "{error_code}" for "{job_id}"')
def service_instance_status_error(context, error_code, job_id):
    settings.cluster = load_system_paasta_config().get_cluster()
    settings.soa_dir = context.soa_dir

    (service, instance, _, __) = decompose_job_id(job_id)

    request = testing.DummyRequest()
    request.matchdict = {'service': service, 'instance': instance}
    response = instance_status(request)

    assert response.status_int == int(error_code)
