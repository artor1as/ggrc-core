# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Module of classes inherited from AbstractTabContainer control (obsolete)."""

from lib import base, users
from lib.constants import element, locator, value_aliases
from lib.utils import selenium_utils


def changelog_tab_validate(_driver, log_panel_element):
  """Validation of all log items on Log pane.
  Return: list of dicts.
  """
  tab_elements = element.AsmtLogTab
  tab_locators = locator.AssessmentLogTab
  selenium_utils.wait_for_js_to_load(_driver)

  def check_log_item(log_element):
    """Check consistency of log item by passed log element.
    Return: dict of bool.
    """
    all_cells_texts = [elem.text for elem in
                       log_element.find_elements(*tab_locators.CELLS_CSS)]
    expected_headers = [tab_elements.FIELD, tab_elements.ORIGINAL_VALUE,
                        tab_elements.NEW_VALUE]
    headers_is_valid = (
        [all_cells_texts.pop(0)
         for _ in xrange(len(expected_headers))] == expected_headers)

    field_is_valid = all(
        cell != "" and cell != tab_elements.EMPTY_STATEMENT
        for cell in all_cells_texts[0::3])
    orignal_value_is_valid = all(
        cell == tab_elements.EMPTY_STATEMENT
        for cell in all_cells_texts[1::3])
    new_value_is_valid = all(
        cell != "" and cell != tab_elements.EMPTY_STATEMENT
        for cell in all_cells_texts[2::3])

    person_element = log_element.find_element(
        *tab_locators.COMMENT_PERSON_CSS)

    return {"headers_is_valid": headers_is_valid,
            "field_is_valid": field_is_valid,
            "orignal_value_is_valid": orignal_value_is_valid,
            "new_value_is_valid": new_value_is_valid,
            "person_is_valid": (
                person_element.text == users.FAKE_SUPER_USER.email)
            }
  selenium_utils.wait_until_not_present(
      _driver, locator.Common.SPINNER_CSS)
  log_list = selenium_utils.get_when_all_visible(
      log_panel_element, tab_locators.LOG_LIST_CSS)
  return [check_log_item(el) for el in log_list]


class DashboardWidget(base.AbstractTabContainer):
  """Class of 'Dashboard' widget which contains one or few tabs."""

  def _tabs(self):
    """If dashboard controller exists set 'tab' items to actual tabs.
    Else set 'tab' items to only one active item.
      - Return: dict of tab members
    """
    if selenium_utils.is_element_exist(self._driver,
                                       self._locators.TAB_CONTROLLER_CSS):
      tabs = {tab_el.text: self.active_tab_elem
              for tab_el in self.tab_controller.get_items()}
    else:
      tabs = {value_aliases.DEFAULT: self.active_tab_elem}
    return tabs

  def _get_locators(self):
    """Return locators of DashboardContainer."""
    return locator.DashboardWidget

  def get_all_tab_names_and_urls(self):
    """Return source urls of all Dashboard members."""
    all_tabs_urls = {}
    for tab_name, tab_el in self._tabs().iteritems():
      if tab_name != value_aliases.DEFAULT:
        self.tab_controller.active_tab = tab_name
      all_tabs_urls[tab_name] = tab_el.get_property("src")
    return all_tabs_urls
