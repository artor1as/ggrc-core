# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Utility classes and functions for tests."""
# pylint: disable=too-few-public-methods
import itertools
import re
import uuid

import tenacity

from lib import constants


def append_random_string(text):
  return text + str(uuid.uuid4())


def prepend_random_string(text):
  return str(uuid.uuid4()) + text


class HtmlParser(object):
  """The HtmlParser class simulates what happens with (non-rich)text in HTML.
 """
  @staticmethod
  def parse_text(text):
    """Simulates text parsed by html.
    Args: text (basestring)
    """
    return re.sub(r'\s+', " ", text)


def wait_for(func):
  """Waits for function to return truthy value."""
  def is_falsy(value):
    """Return whether value if falsy (None or False)."""
    return not value
  return tenacity.Retrying(
      stop=tenacity.stop_after_delay(constants.ux.MAX_USER_WAIT_SECONDS),
      retry=tenacity.retry_if_result(is_falsy))(func)


def assert_wait(func, exc_type=AssertionError):
  """Waits for function to succeed (not raise `exc_type`)."""
  return tenacity.Retrying(
      stop=tenacity.stop_after_delay(constants.ux.MAX_USER_WAIT_SECONDS),
      retry=tenacity.retry_if_exception_type((exc_type, tenacity.TryAgain)))(
      func)


def list_obj_assert(actual_list, expected_list):
  """Assert that list `actual_obj_list` is the same as `expected_obj_list`."""
  for actual, expected in itertools.izip_longest(actual_list, expected_list):
    obj_assert(actual, expected)


def obj_assert(actual_obj, expected_obj):
  """Assert that `actual_obj` is the same as `expected_obj` except keys where
  values are None.
  """
  # Pytest shortens the diff so we have to produce the diff ourselves
  # to workaround this.
  # https://github.com/pytest-dev/pytest/issues/2256
  # https://github.com/pytest-dev/pytest/issues/3632
  # pylint: disable=unidiomatic-typecheck
  assert type(actual_obj) == type(expected_obj)
  actual_obj_dict = actual_obj.obj_dict()
  expected_obj_dict = expected_obj.obj_dict()
  _dict_assert(actual_obj_dict, expected_obj_dict)


def _dict_assert(actual_dict, expected_dict):
  """Assert that dicts are the same."""
  for key in set(actual_dict) & set(expected_dict):
    _value_assert(key, actual_dict[key], expected_dict[key])


def _list_assert(actual_list, expected_list):
  """Assert that lists are them same."""
  for actual, expected in itertools.izip_longest(actual_list, expected_list):
    _value_assert(None, actual, expected)


def _value_assert(current_key, actual_value, expected_value):
  """Assert that values are the same."""
  if actual_value is None:
    return
  if isinstance(actual_value, list) and isinstance(expected_value, list):
    _list_assert(actual_value, expected_value)
  elif isinstance(actual_value, dict) and isinstance(expected_value, dict):
    _dict_assert(actual_value, expected_value)
  else:
    assert actual_value == expected_value, "key: {}".format(current_key)
