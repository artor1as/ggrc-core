# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""GGRC UI utility functions"""
import re

import tenacity

from lib import browsers
from lib.utils import test_utils


def select_user(root, email):
  """Selects user in person autocomplete list."""
  def autocomplete_row():
    """Returns a row with an email."""
    # Iterating through elements may raise exception if elements are removed
    # during iteration
    # (https://github.com/watir/watir/issues/769)
    rows = root.lis(class_name="ui-menu-item")
    # Only user is shown in some cases
    # In others user and "Create" is shown
    if len(rows) in (1, 2):
      row = rows[0]
      if email in row.text:
        return row
    raise tenacity.TryAgain
  row = test_utils.assert_wait(autocomplete_row)
  row.click()


def wait_for_spinner_to_disappear():
  """Waits until there are no spinners on the page."""
  browser = browsers.get_browser()
  browser.wait_until(lambda br: len(br.divs(class_name="spinner")) == 0)


def wait_for_alert(text):
  """Waits for alert with text `text` to appear."""
  browser = browsers.get_browser()
  browser.element(
      class_name="alert-info", text=re.compile(text)).wait_until(
      lambda e: e.present)
