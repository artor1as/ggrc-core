# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Modals for compare and update objects."""

from lib import base
from lib.constants import locator
from lib.utils import selenium_utils


class CompareUpdateObjectModal(base.Modal):
  """Modal for compare version of objects and update them to latest version."""
  # pylint: disable=too-few-public-methods
  _locators = locator.ModalUpdateObject

  def __init__(self):
    super(CompareUpdateObjectModal, self).__init__()
    self.title_modal = base.Label(self._driver, self._locators.MODAL_TITLE)
    self.confirmation_text = base.Label(
        self._driver, self._locators.CONFIRMATION_TEXT)
    self.button_update = base.Button(
        self._driver, self._locators.BUTTON_CONFIRM)

  def confirm_update(self):
    """Confirm update object."""
    selenium_utils.wait_for_js_to_load(self._driver)
    self.button_update.click()
    selenium_utils.get_when_invisible(
        self._driver, self._locators.BUTTON_CONFIRM)
