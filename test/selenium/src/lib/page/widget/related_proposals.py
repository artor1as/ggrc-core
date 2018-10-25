# coding=utf-8
# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Related proposals."""
from lib import base
from lib.entities import entity


class RelatedProposals(base.WithBrowser):
  """Related proposals."""

  def get_proposals(self):
    """Get proposal rows."""
    elements = self._browser.divs(class_name="object-list__item")
    proposal_rows = [ProposalRow(
        row_element=element).get_proposal() for element in elements]
    return proposal_rows

  def has_apply_btn(self, proposal):
    """Check if proposal apply button exists."""
    proposals = self.get_proposals()
    proposal_index = proposals.index(proposal)
    element = self._browser.divs(
        class_name="object-list__item ")[proposal_index]
    return ProposalRow(row_element=element).has_review_apply_btn()


class ProposalRow(object):
  """Proposal row."""

  def __init__(self, row_element):
    self._row_element = row_element

  def get_proposal(self):
    """Get proposal."""
    return entity.ProposalEntity(
        status=self.get_status(), author=self.get_author(),
        changes=self.get_changes(),
        comment=self.get_comment())

  def get_status(self):
    """Get proposal status."""
    return self._row_element.div(class_name="object-history__state").text

  def get_author(self):
    """Get proposal author."""
    return self._row_element.element(
        class_name="object-history__author-info").text.split(' ')[2]

  def get_datetime(self):
    """Get proposal datetime."""
    return self._row_element.element(class_name="object-history__date").text

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
