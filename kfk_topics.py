import click
import os
import io
import yaml

from kfk import kfk
from option_extensions import NotRequiredIf, RequiredIf
from commons import print_missing_options_for_command, download_strimzi_if_not_exists, delete_last_applied_configuration
from constants import *


@click.option('-n', '--namespace', help='Namespace to use', required=True)
@click.option('-c', '--cluster', help='Cluster to use', required=True)
@click.option('--delete-config', help='A topic configuration override to be removed for an existing topic',
              multiple=True)
@click.option('--config', help='A topic configuration override for the topic being created or altered.', multiple=True)
@click.option('--alter', help='Alter the number of partitions, replica assignment, and/or configuration for the topic.',
              is_flag=True)
@click.option('--native', help='List details for the given topic natively.', is_flag=True, cls=RequiredIf,
              required_if='describe')
@click.option('--delete', help='Delete a topic.', is_flag=True)
@click.option('-o', '--output',
              help='Output format. One of: json|yaml|name|go-template|go-template-file|template|templatefile|jsonpath'
                   '|jsonpath-file.')
@click.option('--describe', help='List details for the given topic.', is_flag=True)
@click.option('--replication-factor', help='The replication factor for each partition in the topic being created.',
              cls=RequiredIf, required_if='create')
@click.option('--partitions', help='The number of partitions for the topic being created or altered ', cls=RequiredIf,
              required_if='create')
@click.option('--create', help='Create a new topic.', is_flag=True)
@click.option('--list', help='List all available topics.', is_flag=True)
@click.option('--topic', help='Topic Name', required=True, cls=NotRequiredIf, not_required_if='list')
@kfk.command()
def topics(topic, list, create, partitions, replication_factor, describe, output, delete, native, alter, config,
           delete_config,
           cluster,
           namespace):
    """The kafka topic(s) to be created, altered or described."""

    if list:
        os.system('kubectl get kafkatopics -l strimzi.io/cluster={cluster} -n {namespace}'.format(cluster=cluster,
                                                                                                  namespace=namespace))
    elif create:
        download_strimzi_if_not_exists()

        with open(r'{strimzi_path}/examples/topic/kafka-topic.yaml'.format(strimzi_path=STRIMZI_PATH).format(
                version=STRIMZI_VERSION)) as file:
            topic_dict = yaml.full_load(file)

            topic_dict["metadata"]["name"] = topic
            topic_dict["spec"]["partitions"] = int(partitions)
            topic_dict["spec"]["replicas"] = int(replication_factor)

            add_topic_config(config, topic_dict)

            topic_yaml = yaml.dump(topic_dict)
            os.system(
                'echo "{topic_yaml}" | kubectl create -f - -n {namespace}'.format(strimzi_path=STRIMZI_PATH,
                                                                                  topic_yaml=topic_yaml,
                                                                                  namespace=namespace))

    elif describe:
        if output is not None:
            os.system(
                'kubectl get kafkausers -l strimzi.io/cluster={cluster} -n {namespace} -o {output}'.format(
                    cluster=cluster,
                    namespace=namespace, output=output))
        else:
            if native:
                os.system(
                    'kubectl exec -it {cluster}-kafka-0 -c kafka -n {namespace} -- bin/kafka-topics.sh --bootstrap-server '
                    'localhost:9092 --describe --topic {topic} '.format(cluster=cluster, namespace=namespace,
                                                                        topic=topic))
            else:
                topic_exists = topic in os.popen(
                    'kubectl get kafkatopics -l strimzi.io/cluster={cluster} -n {namespace}'.format(cluster=cluster,
                                                                                                    namespace=namespace)).read()
                if topic_exists:
                    os.system(
                        'kubectl describe kafkatopics {topic} -n {namespace}'.format(topic=topic, namespace=namespace))

    elif delete:
        topic_exists = topic in os.popen(
            'kubectl get kafkatopics -l strimzi.io/cluster={cluster} -n {namespace}'.format(cluster=cluster,
                                                                                            namespace=namespace)).read()
        if topic_exists:
            os.system(
                'kubectl delete kafkatopics {topic} -n {namespace}'.format(topic=topic, namespace=namespace))

    elif alter:
        topic_exists = topic in os.popen(
            'kubectl get kafkatopics -l strimzi.io/cluster={cluster} -n {namespace}'.format(cluster=cluster,
                                                                                            namespace=namespace)).read()
        if topic_exists:
            topic_yaml = os.popen(
                'kubectl get kafkatopics {topic} -n {namespace} -o yaml'.format(topic=topic,
                                                                                namespace=namespace)).read()

            file = io.StringIO(topic_yaml)
            topic_dict = yaml.full_load(file)

            if partitions is not None:
                topic_dict["spec"]["partitions"] = int(partitions)

            if replication_factor is not None:
                topic_dict["spec"]["replicas"] = int(replication_factor)

            delete_last_applied_configuration(topic_dict)

            add_topic_config(config, topic_dict)
            delete_topic_config(delete_config, topic_dict)

            topic_yaml = yaml.dump(topic_dict)
            print(topic_yaml)
            os.system(
                'echo "{topic_yaml}" | kubectl apply -f - -n {namespace} '.format(strimzi_path=STRIMZI_PATH,
                                                                                  topic_yaml=topic_yaml,
                                                                                  namespace=namespace))
    else:
        print_missing_options_for_command("topics")


def add_topic_config(config, topic_dict):
    if type(config) is tuple:
        for config_str in config:
            config_arr = config_str.split('=')
            topic_dict["spec"]["config"][config_arr[0]] = config_arr[1]


def delete_topic_config(delete_config, topic_dict):
    if type(delete_config) is tuple:
        for delete_config_str in delete_config:
            if delete_config_str in topic_dict["spec"]["config"]:
                del topic_dict["spec"]["config"][delete_config_str]
