# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Operations with page tabs"""


class Tabs(object):
  """Represents a container with tab elements."""

  TOP = "top"
  INTERNAL = "internal"

  def __init__(self, container, level):
    if level == self.TOP:
      self._root = container.ul(class_name="internav")
    elif level == self.INTERNAL:
      self._root = container.element(class_name="nav-tabs")
    else:
      raise NotImplementedError

  @property
  def tabs(self):
    """Returns a list of tabs."""
    return [Tab(tab_el) for tab_el in self._root.lis()]

  @property
  def tab_names(self):
    """Returns a list of tab names."""
    return [tab.name for tab in self.tabs]

  @property
  def active_tab(self):
    """Returns active tab."""
    return Tab(self._root.li(class_name="active"))

  def ensure_tab(self, tab_name):
    """Ensure that page tab `tab_name` is opened"""
    if self.active_tab.name != tab_name:
      self._tab_with_name(tab_name).select()

  def _tab_with_name(self, name):
    """Returns tab with name `name`."""
    return Tab(self._root.li(text=name))


class Tab(object):
  """Represents a single tab element."""

  def __init__(self, tab_el):
    self._root = tab_el

  @property
  def name(self):
    """Returns name of the tab."""
    return self._root.text

  def select(self):
    """Selects tab."""
    self._root.click()
