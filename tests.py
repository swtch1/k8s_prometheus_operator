import os
from unittest import TestCase, main
from tempfile import mkstemp

import yaml

from k8s_prometheus_operator import generate_config_files as g


class TestGeneratingConfigFiles(TestCase):
  def test_all_named_files_exist(self):
    # need to ensure that all of the files we expect to exist actually do, mainly just to cover for refactoring
    for f in [
      os.path.join(g.TEMPLATES_DIRECTORY, g.SVC_TEMPLATE_FILE_NAME),
      os.path.join(g.TEMPLATES_DIRECTORY, g.EXTERNAL_SVC_FILE_NAME),
    ]:
      self.assertTrue(os.path.isfile(f), f)

  def test_getting_selectors_from_list_raises_error_wrong_type(self):
    selectors = 'abc'
    with self.assertRaises(AssertionError):
      g.validate_selectors(selectors)

  def test_getting_selectors_from_list_raises_error_on_more_than_one_equal(self):
    selectors = ['key=val', 'key=val=otherval']
    with self.assertRaises(AssertionError):
      g.validate_selectors(selectors)

  def test_getting_selectors_with_empty_selectors_list_returns_empty_dict(self):
    selectors = []
    s = g.get_selectors_map(selectors)
    self.assertTrue(s == {})

  def test_getting_selectors_returns_expected(self):
    tests = [
      {
        'name': 'single_selector',
        'selectors': ['key=val'],
        'expected': {'key': 'val'},
      },
      {
        'name': 'multiple_selectors',
        'selectors': ['key=val', 'foo=bar', 'bar=baz'],
        'expected': {'key': 'val', 'foo': 'bar', 'bar': 'baz'},
      },
      {
        'name': 'mixed_case',
        'selectors': ['fOo=bAz'],
        'expected': {'fOo': 'bAz'},
      },
    ]
    for test in tests:
      s = g.get_selectors_map(test['selectors'])
      self.assertTrue(s == test['expected'], test['name'])

  def test_validating_service_type_raises_error_when_arg_is_not_in_svc_types_list(self):
    tests = [
      {
        'name': 'node_port',
        'in': 'NodePort',
        'expect_raise': False,
      },
      {
        'name': 'load_balancer',
        'in': 'LoadBalancer',
        'expect_raise': False,
      },
      {
        'name': 'mixed_case',
        'in': 'LoAdbAlaNcer',
        'expect_raise': True,
      },
    ]
    for test in tests:
      if test['expect_raise']:
        with self.assertRaises(AssertionError):
          g.validate_service_type(test['in'], g.SVC_TYPES)
      else:
        # since we expect this to raise on error just try to run it
        g.validate_service_type(test['in'], g.SVC_TYPES)

  def test_transforming_file_with_placeholders(self):
    _, src = mkstemp()
    _, dst = mkstemp()
    with open(src, 'w') as f:
      f.write('foo bar ((baz)) bazzer')
    replacement_map = {'((baz))': 'newbaz'}
    expected = 'foo bar newbaz bazzer'
    g.transform_file(src, dst, replacement_map)
    with open(dst, 'r') as f:
      self.assertTrue(f.read() == expected)

  def test_transforming_file_converts_does_not_fail_on_int_in_replace_map(self):
    _, src = mkstemp()
    _, dst = mkstemp()
    with open(src, 'w') as f:
      f.write('foo bar ((someint)) bazzer')
    replacement_map = {'((someint))': 5}
    expected = 'foo bar 5 bazzer'
    g.transform_file(src, dst, replacement_map)
    with open(dst, 'r') as f:
      self.assertTrue(f.read() == expected)

  def test_writing_selectors(self):
    tests = [
      {
        'name': 'single_selector',
        'selectors_map': {'foo': 'bar'},
        'expected_output': {'spec': {'selector': {'foo': 'bar'}}}
      },
    ]
    _, tmp = mkstemp()
    test_yml = '\n'.join([
      'spec:',
      '  selector:',
      '    x: y',  # placeholders which should be removed by function
    ])
    with open(tmp, 'w') as f:
      f.write(test_yml)
    for test in tests:
      g.write_selectors(tmp, test['selectors_map'])
      with open(tmp, 'r') as f:
        self.assertTrue(yaml.load(f) == test['expected_output'], test['name'])

  def test_getting_service_type(self):
    tests = [
      {
        'name': 'basic',
        'in': 'NodePort',
        'expected_output': 'NodePort',
      },
      {
        # the function is NOT supposed to be case sensitive
        'name': 'returns_none_with_incorrect_case',
        'in': 'noDepoRt',
        'expected_output': None,
      },
    ]
    for test in tests:
      t = g.get_service_type(test['in'])
      self.assertTrue(t == test['expected_output'], test['name'])

  def test_getting_service_type_gracefully_handles_none_type_input(self):
    t = g.get_service_type(None)
    self.assertTrue(t is None)


if __name__ == '__main__':
    main()
