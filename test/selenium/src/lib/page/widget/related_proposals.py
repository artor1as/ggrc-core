# coding=utf-8
# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Related proposals."""
from dateutil import tz
from lib import base
from lib.entities import entity
from lib.utils import date_utils


class RelatedProposals(base.WithBrowser):
  """Related proposals."""

  def get_proposals(self):
    """Get proposal rows."""
    elements = self._browser.divs(class_name="object-list__item")
    proposal_rows = [ProposalRow(
        row_element=element).get_proposal() for element in elements]
    return proposal_rows

  def proposal_row(self, proposal):
    """Return proposal row."""
    proposal_index = self.get_proposals().index(proposal)
    element = self._browser.divs(
        class_name="object-list__item ")[proposal_index]
    return ProposalRow(row_element=element)

  def has_apply_btn(self, proposal):
    """Check if proposal apply button exists."""
    return self.proposal_row(proposal).has_review_apply_btn()

  def click_apply_btn(self, proposal):
    """Click on the proposal apply button."""
    self.proposal_row(proposal).click_review_apply_btn()


class ProposalRow(object):
  """Proposal row."""

  def __init__(self, row_element):
    self._row_element = row_element

  def get_proposal(self):
    """Get proposal."""
    return entity.ProposalEntity(
        status=self.get_status(), author=self.get_author(),
        changes=self.get_changes(),
        datetime=self.get_datetime().replace(tzinfo=tz.tzlocal()),
        comment=self.get_comment())

  def get_status(self):
    """Get proposal status."""
    return self._row_element.div(class_name="object-history__state").text

  def get_author(self):
    """Get proposal author."""
    return self._row_element.element(
        class_name="object-history__author-info").text.split(' ')[2]

  def get_datetime(self, as_date=True):
    """Get proposal datetime."""
    # Last 7 symbols are the UTC offset in +(-)HH:MM format. It is not
    # needed here because we have tz.tzlocal() when creating datetime.
    # %z directive is not working if ":" symbol is removed
    # from UTC offset substring.
    datetime_str = self._row_element.element(
        class_name="object-history__date").text[:-7]
    if not as_date:
      return datetime_str
    return date_utils.str_to_datetime(datetime_str, "%m/%d/%Y %I:%M:%S %p")

  def get_changes(self):
    """Get proposal changes."""
    def parse_value(variable):
      """Return None if variable is 'Em dash' else variable."""
      return variable if not variable == u'—' else None

    changes_list = []
    for row in self._row_element.elements(
        class_name="object-history__row--attributes"
    ):
      row_element_texts = [element.text for element in row.elements(
          class_name="flex-size-1")]
      changes = {"obj_attr_type": parse_value(row_element_texts[0]),
                 "cur_value": parse_value(row_element_texts[1]),
                 "proposed_value": parse_value(row_element_texts[2])}
      changes_list.append(changes)
    return changes_list

  def get_comment(self):
    """Get proposal comment."""
    comment = self._row_element.element(
        xpath=("//related-proposals-item/div[@class='flex-size-1 "
               "object-history__attr']")).text
    return None if comment == "" else comment

  def has_review_apply_btn(self):
    """Check if proposal Review&Apply button exists."""
    return self._row_element.element(tag_name="button").exists

  def click_review_apply_btn(self):
    """Click on the proposal review and apply button."""
    self._row_element.element(tag_name="button").click()
