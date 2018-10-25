# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Generic three bbs elements."""


class ThreeBbs(object):
  """Represents 3bbs element with dropdown list."""

  def __init__(self, container):
    self._root = container
    self._three_bbs_el = self._root.element(class_name="btn-3bbps")
    self._options_root = self._three_bbs_el.next_sibling(
        class_name="dropdown-menu")

  def _open(self):
    """Opens dropdown list."""
    self._three_bbs_el.click()

  def select_option_by_text(self, text):
    """Chooses list option by text."""
    self._open()
    self._options_root.link(text=text).click()

  def option_by_text(self, text):
    """Returns an option by text."""
    self._open()
    return ThreeBbsOption(self._options_root.element(text=text))

  def option_by_icon_cls(self, fa_icon_cls):
    """Returns an option by icon class."""
    self._open()
    return ThreeBbsOption(self._options_root.element(
        class_name=fa_icon_cls).parent())

  @property
  def exists(self):
    """Returns whether 3bbs element exists."""
    return self._three_bbs_el.exists


class ThreeBbsOption(object):
  """Represents three bbs option."""

  def __init__(self, root):
    self._root = root

  def click(self):
    """Selects an option."""
    self._root.click()

  @property
  def exists(self):
    """Returns whether the option exists."""
    return self._root.exists
