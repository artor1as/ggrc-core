# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Mixins for info page objects"""
# pylint: disable=too-few-public-methods

from lib import base
from lib.element import page_elements


class WithPageElements(base.WithBrowser):
  """A mixin for page elements"""

  def _related_people_list(self, label):
    """Return RelatedPeopleList page element with label `label`"""
    return page_elements.RelatedPeopleList(self._browser, label)

  def _related_urls(self, label):
    """Return RelatedUrls page element with label `label`"""
    return page_elements.RelatedUrls(self._browser, label)

  def _assessment_evidence_urls(self):
    """Return AssessmentEvidenceUrls page element"""
    return page_elements.AssessmentEvidenceUrls(self._browser)

  def _comment_area(self):
    """Return CommentArea page element"""
    return page_elements.CommentArea(self._browser)

  def _simple_field(self, label):
    """Returns SimpleField page element."""
    return page_elements.SimpleField(self._browser, label)

  def _info_pane_form_field(self, label):
    """Returns InfoPaneFormField page element."""
    return page_elements.InfoPaneFormField(self._browser, label)

  def _assessment_form_field(self, label):
    """Returns AssessmentFormField page element."""
    return page_elements.AssessmentFormField(self._browser, label)


class WithAssignFolder(base.WithBrowser):
  """A mixin for `Assign Folder`"""

  def __init__(self, driver):
    super(WithAssignFolder, self).__init__(driver)
    self.assign_folder_button = self._browser.element(
        class_name="mapped-folder__add-button")


class WithObjectReview(base.WithBrowser):
  """A mixin for object reviews"""

  def __init__(self, driver):
    super(WithObjectReview, self).__init__(driver)
    self.request_review_btn = self._browser.button(text="Request Review")
