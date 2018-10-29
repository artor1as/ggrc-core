# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Facade for Proposal UI services"""
# pylint: disable=invalid-name
import copy

from lib import base
from lib.entities import entity
from lib.entities.entity import Representation
from lib.page.proposal_digest import ProposalDigest
from lib.service import proposal_ui_service, proposal_email_service


def create_proposal(selenium, obj):
  """Create a proposal to obj."""
  return proposal_ui_service.ProposalsService(selenium).create_proposal(obj)


def apply_proposal(selenium, obj, proposal):
  """Apply an obj proposal."""
  proposal_service = proposal_ui_service.ProposalsService(selenium)
  proposal_service.apply_proposal(obj, proposal)


def get_related_proposals(selenium, obj):
  """Get related proposals."""
  return proposal_ui_service.ProposalsService(
      selenium).get_related_proposals(obj)


def get_expected_proposal_email(obj, proposal, proposal_author):
  """Get proposal email."""
  proposal_copy = copy.deepcopy(proposal)
  for change in proposal_copy.changes:
    change.pop("cur_value", None)
  person_name = proposal_author.name
  expected_email = entity.ProposalEmailUI(
      recipient_email=obj.admins[0], author=person_name,
      obj_type=obj.type.lower(), changes=proposal_copy.changes,
      comment=proposal_copy.comment)
  return expected_email


def assert_proposal_apply_btns_exist(
    selenium, obj, proposals, apply_btn_exists
):
  """Check proposal apply buttons existence."""
  actual_apply_btns_existence = [
      proposal_ui_service.ProposalsService(
          selenium).has_proposal_apply_btn(obj, proposal)
      for proposal in proposals]
  exp_apply_btns_existence = [apply_btn_exists] * len(proposals)
  assert exp_apply_btns_existence == actual_apply_btns_existence


def assert_proposal_notification_connects_to_obj(
    selenium, obj, proposal, proposal_author
):
  """Check if proposal notification email exists."""
  proposal_digest_service = (
      proposal_email_service.ProposalDigestService(selenium))
  proposal_digest_service.open_proposal_digest()
  proposal_email = get_expected_proposal_email(obj, proposal, proposal_author)
  assert proposal_email in ProposalDigest().get_proposal_emails()
  base.Test.general_equal_assert(
      copy.deepcopy(obj).repr_ui(),
      proposal_digest_service.opened_obj(obj, proposal_email),
      "modified_by", *Representation.tree_view_attrs_to_exclude)
