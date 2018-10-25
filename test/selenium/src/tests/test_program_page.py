# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Program page smoke tests."""
# pylint: disable=no-self-use

import pytest
from selenium.webdriver.common import keys

from lib import base, users
from lib.constants import locator
from lib.entities import entities_factory
from lib.page.widget import object_modal
from lib.service import webui_service, rest_facade


class TestProgramPage(base.Test):
  """Tests for program page."""

  @pytest.mark.smoke_tests
  def test_info_tab_is_active_by_default(self, program, selenium):
    """Verifies Info tab is active by default."""
    # pylint: disable=invalid-name
    info_page = webui_service.ProgramsService(
        selenium).open_info_page_of_obj(program)
    active_tab_name = info_page.top_tabs.active_tab.name
    assert active_tab_name == "Program Info"

  @pytest.mark.smoke_tests
  def test_permalink(self, selenium, program):
    """Verify url is copied to clipboard."""
    info_page = webui_service.ProgramsService(
        selenium).open_info_page_of_obj(program)
    info_page.three_bbs.select_get_permalink()
    # test notification alert
    base.AnimatedComponent(
        selenium, [locator.WidgetInfoProgram.ALERT_LINK_COPIED],
        wait_until_visible=True)
    # test generated link
    # Doesn't work on Mac as Chromedriver / Devtools emulate keys on browser
    # level (Cmd + V works on OS level).
    # https://github.com/GoogleChrome/puppeteer/issues/1313
    # https://bugs.chromium.org/p/chromedriver/issues/detail?id=30
    info_page.three_bbs.select_edit()
    modal = object_modal.get_modal_obj("program", selenium)
    modal.title_field.set(keys.Keys.CONTROL, "v")
    assert modal.title_field.value == program.url

  @pytest.mark.smoke_tests
  def test_create_program(self, selenium):
    """Tests program creation via UI."""
    program = entities_factory.ProgramsFactory().create()
    actual_program = webui_service.ProgramsService(
        selenium).create_obj_and_get_obj(program)
    rest_program = rest_facade.get_obj(actual_program)
    program.update_attrs(
        created_at=rest_program.created_at,
        updated_at=rest_program.updated_at,
        modified_by=users.current_user(),
        slug=rest_program.slug,
        url=rest_program.url).repr_ui()
    self.general_equal_assert(program, actual_program, "custom_attributes")

  @pytest.mark.smoke_tests
  def test_edit_program(self, program, selenium):
    """Tests if data is saved after editing program info page edit modal."""
    new_title = "[EDITED] " + program.title
    program_service = webui_service.ProgramsService(selenium)
    program_service.edit_obj(program, title=new_title)
    actual_program = program_service.get_obj_from_info_page(program)
    program.update_attrs(
        title=new_title,
        updated_at=rest_facade.get_obj(actual_program).updated_at).repr_ui()
    self.general_equal_assert(program, actual_program)
