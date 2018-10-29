# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Modal for comparing object versions and apply or decline the proposal."""

from lib import base
from lib.utils import selenium_utils


class CompareApplyDeclineModal(base.Modal):
  """Modal for comparing object versions and apply or decline the proposal."""
  # pylint: disable=too-few-public-methods

  def __init__(self, driver=None):
    super(CompareApplyDeclineModal, self).__init__(driver)
    self._modal = self._browser.div(class_name="compare-modal")
    self._apply_btn = self._modal.button(text="Apply")

  def click_apply_btn(self):
    """Click on the apply button."""
    selenium_utils.wait_for_js_to_load(self._driver)
    self._apply_btn.click()
    self._modal.wait_until_not_present()
