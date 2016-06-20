#!/usr/bin/env python
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
"""
PaaSTA service instance status/start/stop etc.
"""
import json
import logging
import traceback

from pyramid.response import Response
from pyramid.view import view_config

from paasta_tools import marathon_tools
from paasta_tools.api import settings
from paasta_tools.cli.cmds.status import get_actual_deployments
from paasta_tools.marathon_serviceinit import compose_marathon_job_instance_count
from paasta_tools.marathon_serviceinit import deploy_status_marathon_job
from paasta_tools.marathon_serviceinit import get_bouncing_status
from paasta_tools.utils import NoDockerImageError
from paasta_tools.utils import PaastaColors
from paasta_tools.utils import validate_service_instance


log = logging.getLogger(__name__)


def chronos_instance_status(instance_status, service, instance, verbose):
    return


def marathon_job_status(client, job_config):
    mstatus = {}

    try:
        app_id = job_config.format_marathon_app_dict()['id']
        mstatus['app_id'] = app_id
    except NoDockerImageError:
        error_msg = "Docker image is not in deployments.json. Has Jenkins deployed it?"
        mstatus['message'] = error_msg
        return mstatus

    if marathon_tools.is_app_id_running(app_id, client):
        app = client.get_app(app_id)
        mstatus['deploy_status'] = PaastaColors.decolor(
            deploy_status_marathon_job(app, app_id, client))

        running_instances = app.tasks_running
        mstatus['running_instances'] = running_instances
        normal_instance_count = job_config.get_instances()
        mstatus['normal_instance_count'] = normal_instance_count

        status, instance_count = compose_marathon_job_instance_count(
            running_instances, normal_instance_count)
        mstatus['status'] = PaastaColors.decolor(status)

    else:
        mstatus['status'] = 'Critical'
        mstatus['deploy_status'] = 'Not Running'

    return mstatus


def marathon_instance_status(instance_status, service, instance, verbose):
    marathon_config = marathon_tools.load_marathon_config()
    client = marathon_tools.get_marathon_client(marathon_config.get_url(),
                                                marathon_config.get_username(),
                                                marathon_config.get_password())
    job_config = marathon_tools.load_marathon_service_config(
        service, instance, settings.cluster, soa_dir=settings.soa_dir)

    instance_status['state'] = PaastaColors.decolor(
        get_bouncing_status(service, instance, client, job_config))
    instance_status['desired state'] = PaastaColors.decolor(
        job_config.get_desired_state_human())
    instance_status['marathon'] = marathon_job_status(client, job_config)


def error_wrapper(error_message, error_code):
    log.error(error_message)

    response = Response(
        body=json.dumps({'message': error_message}),
        content_type='application/json')
    response.status_int = error_code
    return response


@view_config(route_name='service.instance.status', request_method='GET', renderer='json')
def instance_status(request):
    service = request.matchdict['service']
    instance = request.matchdict['instance']
    verbose = request.matchdict.get('verbose', False)

    actual_deployments = get_actual_deployments(service, settings.soa_dir)

    instance_status = {}
    instance_status['service'] = service
    instance_status['instance'] = instance

    deployment_key = '.'.join([settings.cluster, instance])
    if deployment_key not in actual_deployments:
        error_message = 'deployment key %s not found' % deployment_key
        return error_wrapper(error_message, 404)

    version = actual_deployments[deployment_key][:8]
    instance_status['git sha'] = version

    try:
        instance_type = validate_service_instance(service, instance, settings.cluster, settings.soa_dir)
        if instance_type == 'marathon':
            marathon_instance_status(instance_status, service, instance, verbose)
        elif instance_type == 'chronos':
            chronos_instance_status(instance_status, service, instance, verbose)
        else:
            error_message = 'Unknown instance_type %s of %s.%s' % (instance_type, service, instance)
            return error_wrapper(error_message, 404)
    except:
        error_message = traceback.format_exc()
        return error_wrapper(error_message, 500)

    return instance_status
