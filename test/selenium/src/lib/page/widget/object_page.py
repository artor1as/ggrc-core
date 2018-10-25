# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Represents a page with the url of some object."""
import re

from lib import base, environment, url
from lib.element import tab_element
from lib.utils import selenium_utils


class ObjectPage(base.WithBrowser):
  """Represents some tab of some object page."""

  @staticmethod
  def _url_fragment():
    """Returns url fragment of the page that can be navigated to.
     May be overridden in a subclass.
     """
    pass

  def wait_to_be_init(self):
    """Waits for page to be fully initialized.
    May be overridden in a subclass.
    """
    pass

  def open_via_url(self, obj):
    """Opens the tab via URL."""
    selenium_utils.open_url(url.obj_tab_url(obj, self._url_fragment()))
    self.wait_to_be_init()

  @property
  def top_tabs(self):
    """Returns Tabs page elements for top page tabs."""
    return tab_element.Tabs(self._browser, tab_element.Tabs.TOP)

  def _get_url_match(self):
    """Returns instance of re.MatchObject for current page url."""
    current_url = self._browser.url
    pattern = r"{}\w+/(\d+)".format(environment.app_url)
    return re.search(pattern, current_url)

  def get_url(self):
    """Gets url of the object if page relates to the object."""
    match = self._get_url_match()
    if match:
      return match.string
    return None

  def get_obj_id(self):
    """Gets id of the object (if possible)."""
    match = self._get_url_match()
    if match:
      return match.group(1)
    return None

  def get_current_url_fragment(self):
    """Returns url fragment of the current page."""
    current_url = self._browser.url
    return current_url.split("#!")[1]
