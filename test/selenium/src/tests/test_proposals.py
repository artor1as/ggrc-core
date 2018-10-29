# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Tests for Proposals"""
# pylint: disable=invalid-name
# pylint: disable=no-self-use
# pylint: disable=unused-argument
import pytest

from lib import base, users
from lib.constants import roles, object_states
from lib.service import rest_facade, proposal_ui_facade, proposal_rest_service


class TestProposals(base.Test):
  """Tests for Proposals"""
  _data = None

  @pytest.fixture(scope="class")
  def control_reader_role(self):
    """Create Control role with only read permission."""
    return rest_facade.create_access_control_role(
        object_type="Control",
        read=True, update=False, delete=False)

  @pytest.fixture()
  def test_data(self, control_reader_role, selenium):
    """Create 2 GC users.
    GC 1 creates Control and adds GC 2 as a control reader.
    """
    if not TestProposals._data:
      control_creator = rest_facade.create_user_with_role(roles.CREATOR)
      proposal_creator = rest_facade.create_user_with_role(roles.CREATOR)
      global_reader = rest_facade.create_user_with_role(roles.READER)
      users.set_current_user(control_creator)
      control_custom_roles = [
          (control_reader_role.name, control_reader_role.id,
           [proposal_creator])]
      control = rest_facade.create_control(custom_roles=control_custom_roles)
      users.set_current_user(proposal_creator)
      proposal = proposal_ui_facade.create_proposal(selenium, control)
      users.set_current_user(control_creator)
      proposal.datetime = (
          proposal_rest_service.ProposalsService().
          get_proposal_creation_date(control, proposal))
      users.set_current_user(global_reader)
      proposal_from_gr = proposal_ui_facade.create_proposal(selenium, control)
      proposal_from_gr.datetime = (
          proposal_rest_service.ProposalsService().
          get_proposal_creation_date(control, proposal_from_gr))
      TestProposals._data = {"control_creator": control_creator,
                             "proposal_creator": proposal_creator,
                             "global_reader": global_reader,
                             "control": control,
                             "proposal": proposal,
                             "proposal_from_gr": proposal_from_gr}
    return TestProposals._data

  @pytest.fixture()
  def apply_proposal(self, test_data, selenium):
    """Apply proposal."""
    if test_data["proposal"].status == object_states.PROPOSED:
      users.set_current_user(test_data["control_creator"])
      proposal_ui_facade.apply_proposal(
          selenium, test_data["control"], test_data["proposal"])

  @classmethod
  def check_ggrc_5091(cls, login_user, condition):
    """Check if it is xfail because of GGRC-5091 or fail."""
    if login_user == "proposal_creator":
      base.Test().check_xfail_or_fail(
          condition, "Issue GGRC-5091",
          "There are no proposals in the list from ui.")

  @pytest.mark.parametrize(
      "login_user",
      ["control_creator", "global_reader", "proposal_creator"]
  )
  def test_check_proposals(
      self, login_user, test_data, selenium
  ):
    """Check proposal is created on Change Proposal tab."""
    users.set_current_user(test_data[login_user])
    exp_visible_proposals = [test_data["proposal_from_gr"],
                             test_data["proposal"]]
    self.check_ggrc_5091(
        login_user,
        exp_visible_proposals == proposal_ui_facade.get_related_proposals(
            selenium, test_data["control"]))
    assert exp_visible_proposals == proposal_ui_facade.get_related_proposals(
        selenium, test_data["control"])

  @pytest.mark.parametrize(
      "login_user, apply_btns_exist",
      [("control_creator", True), ("global_reader", False),
       ("proposal_creator", False)]
  )
  def test_check_proposals_apply_btn(
      self, login_user, apply_btns_exist, test_data, selenium
  ):
    """Check proposal apply buttons exist for proposal recipient and do
    not exist for proposal creators."""
    users.set_current_user(test_data[login_user])
    exp_proposals = [test_data["proposal_from_gr"],
                     test_data["proposal"]]
    self.check_ggrc_5091(
        login_user,
        exp_proposals == proposal_ui_facade.get_related_proposals(
            selenium, test_data["control"]))
    proposal_ui_facade.assert_proposal_apply_btns_exist(
        selenium, test_data["control"], exp_proposals, apply_btns_exist)

  @pytest.mark.parametrize(
      "proposal, proposal_author",
      [("proposal", "proposal_creator"),
       ("proposal_from_gr", "global_reader")]
  )
  def test_check_proposals_email_connects_to_correct_obj(
      self, test_data, proposal, proposal_author, selenium
  ):
    """Check if proposal notification email connects to the correct obj."""
    users.set_current_user(users.FAKE_SUPER_USER)
    proposal_ui_facade.assert_proposal_notification_connects_to_obj(
        selenium, test_data["control"], test_data[proposal],
        test_data[proposal_author])

  @pytest.mark.parametrize(
      "login_user",
      ["control_creator", "global_reader", "proposal_creator"]
  )
  def test_check_proposals_applying(
      self, login_user, test_data, apply_proposal, selenium
  ):
    """Check if a proposal is applied."""
    users.set_current_user(test_data[login_user])
    self.check_ggrc_5091(
        login_user,
        ([test_data["proposal_from_gr"], test_data["proposal"]] ==
         proposal_ui_facade.get_related_proposals(
            selenium, test_data["control"])))
    assert test_data["proposal"] in proposal_ui_facade.get_related_proposals(
        selenium, test_data["control"])

  def test_check_proposals_apply_btn_after_applying(
      self, test_data, apply_proposal, selenium
  ):
    """Check an applied proposal apply button does not exist."""
    users.set_current_user(test_data["control_creator"])
    exp_proposals = [test_data["proposal"]]
    proposal_ui_facade.assert_proposal_apply_btns_exist(
        selenium, test_data["control"], exp_proposals, False)
