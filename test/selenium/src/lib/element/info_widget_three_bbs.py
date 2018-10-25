# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""3bbs element for info widget."""
from lib.element import three_bbs
from lib.page.modal import clone_object, delete_object, update_object


class InfoWidgetThreeBbbs(object):
  """3bbs element for info widget."""

  def __init__(self, root):
    self._root = root
    self._three_bbs = three_bbs.ThreeBbs(self._root)

  @property
  def edit_option(self):
    """Returns `Edit <Object>` option."""
    return self._three_bbs.option_by_icon_cls("fa-pencil-square-o")

  def select_edit(self):
    """Selects `Edit <Object>` option."""
    self.edit_option.click()

  def select_get_permalink(self):
    """Selects `Get permalink` option."""
    self._three_bbs.option_by_text("Get permalink").click()

  @property
  def open_option(self):
    """Returns `Open <object>` option.`"""
    return self._three_bbs.option_by_icon_cls("fa-long-arrow-right")

  @property
  def unmap_option(self):
    """Returns `Unmap` option."""
    return self._three_bbs.option_by_text("Unmap")

  def select_delete(self):
    """Selects `Delete` option.
    Return: modal.delete_object.DeleteObjectModal
    """
    self._three_bbs.option_by_text("Delete").click()
    return delete_object.DeleteObjectModal(self._root.browser.driver)

  @property
  def exists(self):
    """Returns whether 3bbs element exists."""
    return self._three_bbs.exists


class AuditInfoWidgetThreeBbbs(InfoWidgetThreeBbbs):
  """3bbs element for Audit info widget."""

  def select_update_objs(self):
    """Selects `Update objects to latest version` option.
    Return: update_object.CompareUpdateObjectModal
    """
    self._three_bbs.option_by_text("Update objects to latest version").click()
    return update_object.CompareUpdateObjectModal()

  def select_clone(self):
    """Selects `Clone <Object>` option.
    Return: clone_object.CloneAuditModal
    """
    self._three_bbs.option_by_icon_cls("fa-clone").click()
    return clone_object.CloneAuditModal(self._root.browser.driver)


class AssessmentInfoWidgetThreeBbbs(InfoWidgetThreeBbbs):
  """3bbs element for Assessment info widget."""

  def select_deprecate(self):
    """Selects `Deprecate` option."""
    self._three_bbs.option_by_text("Deprecate").click()
