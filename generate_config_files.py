import os
import sys
import shutil
import argparse

import yaml

CUR_DIR = os.path.dirname(__file__)
# location of custom application templates
TEMPLATES_DIRECTORY = os.path.join(CUR_DIR, 'custom_app_templates')
# name of the service template because it cannot be handled with string replacement only
SVC_TEMPLATE_FILE_NAME = 'svc_template.yml'
# we need to cleanup this file if it's not used least it be applied with a placeholder value which will fail
EXTERNAL_SVC_FILE_NAME = 'external_svc_template.yml'
# acceptable service types for argument parser
SVC_TYPES = ['NodePort', 'LoadBalancer']
# where modified files will be written
OUTPUT_DIRECTORY = os.path.join(CUR_DIR, 'my_app')
# string in files to be replaced by Kubernetes namespace
NAMESPACE_PLACEHOLDER = '((NAMESPACE))'
# string in files to be replaced by application port being monitored
PORT_PLACEHOLDER = '((APPLICATION_PORT))'
# string in files to be replaced by the exposed service type
SVC_TYPE_PLACEHOLDER = '((SVC_TYPE))'

__description__ = '''
Generate all Kubernetes configuration files necessary to monitor an application with Prometheus. Generate the
configuration files, apply, and expose.
'''
parser = argparse.ArgumentParser(
  description=__description__,
  formatter_class=argparse.RawTextHelpFormatter,
)
parser.add_argument(
  '-n',
  '--namespace',
  help='Namespace in which the application lives.',
  required=True,
)
parser.add_argument(
  '-p',
  '--port',
  help='Port that the application is listening on.',
  type=int,
  required=True,
)
parser.add_argument(
  '-t',
  '--service-type',
  help='Expose the Prometheus server as a Kubernetes service with this service type. Acceptable values are {}'.format(SVC_TYPES),
  required=False,
)
parser.add_argument(
  '-s',
  '--selectors',
  help='''Key value pairs of selectors for the service template in the form of key=value. This should match the label
of the application pods to target. For example, to target an application with the label 'app: myapp' the selector value
would be app=myapp.
Example Usage:
  python {} ... --selectors app=myapp version=v3

All selectors must match for a resource to be selected by the service.
To see the labels for your application run `kubectl get pods --show-labels`
  '''.format(sys.argv[0]),
  nargs='+',
  required=True,
)


def validate_selectors(selectors: list):
  """
  Validate selectors meets all of the necessary requirements. Raise errors if conditions are not met.
  """
  if not isinstance(selectors, list):
    raise AssertionError('selectors must be a list')

  for selector in selectors:
    if selector.count('=') != 1:
      raise AssertionError('selector {} is not valid, each selector must have exactly one "="'.format(selector))


def validate_service_type(service_type, accepted_types):
  if service_type not in accepted_types:
    raise AssertionError('service type {} must be one of {}'.format(service_type, accepted_types))


def get_selectors_map(selectors: list) -> dict:
  """
  Turn argument selectors list into dictionary.
  """
  s_map = {}
  for selector in selectors:
    key, val = selector.split('=')
    s_map[key] = val
  return s_map


def transform_file(src_file, dest_file, r_map):
  """
  Replace all replacement patterns in a file with their valid replacements.

  :param src_file: source file to read from
  :param dest_file: destination file to write to
  :param r_map: replacement map containting values to replace
  """
  with open(src_file, 'r') as f:
    text = f.read()
    for replace_str, replacement in r_map.items():
      text = text.replace(replace_str, str(replacement))
  print('writing {}'.format(dest_file))
  with open(dest_file, 'w') as f:
    f.write(text)


def write_selectors(path: str, selectors_map: dict):
  """
  Write selectors to a Kubernetes Service YAML file.
  The file at path will be overwritten.

  :param path: file to update with selectors map
  :param selectors_map: dictionary of selectors to write
  """
  with open(path, 'r') as f:
    svc_template = yaml.load(f)
  svc_template['spec']['selector'] = {}
  print('overwriting selectors in {}'.format(path))
  for k, v in selectors_map.items():
    svc_template['spec']['selector'][k] = v
  with open(path, 'w') as f:
    yaml.dump(svc_template, f, default_flow_style=False)


def get_service_type(input_type):
  """
  Given an input type, match and return the service type from options.
  Match case explicitly.
  """
  if not input_type:
    return None

  t = [t for t in SVC_TYPES if t == input_type]
  if len(t) != 1:
    return
  return t[0]


def main():
  validate_selectors(args.selectors)
  validate_service_type(args.service_type, SVC_TYPES)
  print('output dir is {}'.format(OUTPUT_DIRECTORY))

  # cleanup the output dir
  if os.path.isdir(OUTPUT_DIRECTORY):
    shutil.rmtree(OUTPUT_DIRECTORY)
  os.mkdir(OUTPUT_DIRECTORY)

  # define map of strings we plan to replace from template files
  replacement_map = {
    NAMESPACE_PLACEHOLDER: args.namespace,
    PORT_PLACEHOLDER: args.port,
    SVC_TYPE_PLACEHOLDER: args.service_type,
  }
  # write all of the template files into the new directory, replacing placeholders along the way
  for template_file in os.scandir(TEMPLATES_DIRECTORY):
    transform_file(template_file.path, os.path.join(OUTPUT_DIRECTORY, template_file.name), replacement_map)

  # we need to handle the selectors in the service template with yaml since it's a dynamic number of elments
  svc_template_file = os.path.join(OUTPUT_DIRECTORY, SVC_TEMPLATE_FILE_NAME)
  write_selectors(svc_template_file, get_selectors_map(args.selectors))

  print('done.')
  print('---')
  print('once prometheus-operator is running in the cluster execute `kubectl create -f ...` for all of the files in {}'.format(OUTPUT_DIRECTORY))
  print('if the prometheus-prometheus pod is running in your namespace then everything was likely successful')

  svc_type = get_service_type(args.service_type)
  if not svc_type:
    os.remove(os.path.join(OUTPUT_DIRECTORY, EXTERNAL_SVC_FILE_NAME))
    print('expose the prometheus-prometheus pod to verify targets are being scraped')
    return

  print('view exposed prometheus service information with `kubectl get svc prometheus --namespace {}`'.format(args.namespace))


if __name__ == '__main__':
  args = parser.parse_args()
  main()
