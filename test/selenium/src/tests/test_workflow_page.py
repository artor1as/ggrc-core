# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Workflow smoke tests."""
# pylint: disable=no-self-use
# pylint: disable=unused-argument
import datetime

import pytest

from lib import base
from lib.entities import (
    app_entity_factory, ui_dict_convert, cycle_entity_creation)
from lib.page.widget import workflow_tabs, object_modal, object_page
from lib.ui import workflow_ui_facade, ui_facade
from lib.utils import test_utils, date_utils


class TestCreateWorkflow(base.Test):
  """Tests for checking results of workflow creation."""

  @pytest.fixture()
  def workflow(self):
    """Create workflow via UI."""
    workflow = app_entity_factory.WorkflowFactory().create()
    app_entity_factory.TaskGroupFactory().create(workflow=workflow)
    workflow_ui_facade.create_workflow(workflow)
    return workflow

  def test_setup_tab_is_opened_after_workflow_ui_creation(
      self, selenium, workflow
  ):
    """Test that creation of workflow via UI redirects to Setup tab."""
    # pylint: disable=invalid-name
    workflow_tabs.SetupTab().wait_to_be_init()
    assert ui_facade.active_tab_name() == "Setup (1)"

  def test_workflow_info_page_after_workflow_ui_creation(
      self, selenium, workflow
  ):
    """Test that creation of workflow via UI corrects a correct object."""
    # pylint: disable=invalid-name
    actual_workflow = ui_facade.get_obj(workflow)
    test_utils.obj_assert(actual_workflow, workflow)

  def test_task_group_created_after_workflow_ui_creation(
      self, selenium, workflow
  ):
    """Test that creation of workflow via UI creates a task group."""
    # pylint: disable=invalid-name
    actual_task_groups = workflow_ui_facade.task_group_objs(
        workflow)
    test_utils.list_obj_assert(actual_task_groups, workflow.task_groups)


class TestWorkflowSetupTab(base.Test):
  """Test actions available on workflow Setup tab."""

  def test_default_values_in_create_task_popup(
      self, app_workflow, app_task_group, selenium
  ):
    """Test expected default values in Create Task popup."""
    # pylint: disable=invalid-name
    workflow_ui_facade.open_create_task_group_task_popup(app_task_group)
    task_modal = object_modal.get_modal_obj("task_group_task")
    actual_start_date = ui_dict_convert.str_to_date(
        task_modal.get_start_date())
    actual_due_date = ui_dict_convert.str_to_date(
        task_modal.get_due_date())
    assert actual_start_date == date_utils.first_not_weekend_day(
        datetime.date.today())
    assert actual_due_date == actual_start_date + datetime.timedelta(days=7)

  def test_create_task_group_task(
      self, app_workflow, app_task_group, app_person, selenium
  ):
    """Test creation of Task Group Task."""
    task = app_entity_factory.TaskGroupTaskFactory().create(
        task_group=app_task_group, assignees=[app_person])
    workflow_ui_facade.create_task_group_task(task)
    actual_tasks = workflow_ui_facade.get_task_group_tasks_objs()
    test_utils.list_obj_assert(actual_tasks, [task])

  def test_add_obj_to_task_group(
      self, app_workflow, app_task_group, app_control, selenium
  ):
    """Test mapping of object to a task group."""
    workflow_ui_facade.add_obj_to_task_group(
        obj=app_control, task_group=app_task_group)
    selenium.refresh()  # reload page to check mapping is saved
    objs = workflow_ui_facade.get_objs_added_to_task_group(app_task_group)
    if not objs:
      pytest.xfail("This is a bug, see GGRC-6125")
    test_utils.list_obj_assert(objs, [app_control])

  def test_delete_task_group(self, app_workflow, app_task_group, selenium):
    """Test deletion of task group."""
    workflow_ui_facade.delete_task_group(app_task_group)
    assert not workflow_ui_facade.task_group_objs(app_workflow)
    assert ui_facade.active_tab_name() == "Setup (0)"


class TestActivateWorkflow(base.Test):
  """Test workflow activation and actions available after activation."""

  @pytest.fixture()
  def activate_workflow(
      self, app_workflow, app_task_group, app_task_group_task, selenium
  ):
    """Activates workflow."""
    workflow_ui_facade.activate_workflow(app_workflow)

  def test_active_cycles_tab_after_workflow_activation(
      self, activate_workflow
  ):
    """Test Active Cycles tab after activation of workflow."""
    # pylint: disable=invalid-name
    assert ui_facade.active_tab_name() == "Active Cycles (1)"

  def test_history_tab_after_workflow_activation(self, activate_workflow):
    """Test History tab after activation of workflow."""
    # pylint: disable=invalid-name
    assert "History (0)" in object_page.ObjectPage().top_tabs.tab_names

  def test_active_cycles_task_tree(self, activate_workflow, app_workflow):
    """Test active cycles tree."""
    workflow_cycles = workflow_ui_facade.get_workflow_cycles(
        app_workflow)
    expected_workflow_cycle = cycle_entity_creation.create_workflow_cycle(
        app_workflow)
    test_utils.list_obj_assert(workflow_cycles, [expected_workflow_cycle])

  def test_map_obj_to_cycle_task(
      self, activate_workflow, app_workflow, app_control, selenium
  ):
    """Test mapping of obj to a cycle task."""
    cycle_task = cycle_entity_creation.create_workflow_cycle(
        app_workflow).cycle_task_groups[0].cycle_tasks[0]
    workflow_ui_facade.map_obj_to_cycle_task(
        obj=app_control, cycle_task=cycle_task)
    selenium.refresh()  # reload page to check mapping is saved
    objs = workflow_ui_facade.get_objs_mapped_to_cycle_task(cycle_task)
    test_utils.list_obj_assert(objs, [app_control])
