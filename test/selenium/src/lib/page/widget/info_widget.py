# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Info widgets."""
# pylint: disable=useless-super-delegation

import re
import time

from selenium.webdriver.common.by import By

from lib import base
from lib.constants import (
    locator, objects, element, roles, regex, messages)
from lib.constants.locator import WidgetInfoAssessment, WidgetInfoControl
from lib.element import (
    info_widget_three_bbs, page_elements, tables, tab_element, tab_containers)
from lib.entities import app_entity_factory
from lib.page.modal.set_value_for_asmt_ca import SetValueForAsmtDropdown
from lib.page.widget import (
    info_panel, object_modal, object_page, related_proposals)
from lib.page.widget.page_mixins import (WithAssignFolder, WithObjectReview,
                                         WithPageElements)
from lib.utils import selenium_utils, help_utils, ui_utils


class InfoWidget(WithPageElements, base.Widget, object_page.ObjectPage):
  """Abstract class of common info for Info pages and Info panels."""
  # pylint: disable=too-many-public-methods
  # pylint: disable=too-many-instance-attributes
  # pylint: disable=protected-access
  _locators = locator.CommonWidgetInfo
  _elements = element.Common
  _dropdown_settings_cls = info_widget_three_bbs.InfoWidgetThreeBbbs
  locator_headers_and_values = None
  _reference_url_label = "Reference URL"
  _evidence_url_label = "Evidence URL"

  def __init__(self, _driver=None):
    super(InfoWidget, self).__init__()
    self.child_cls_name = self.__class__.__name__
    self.obj_name = objects.get_singular(self.child_cls_name)
    self.is_asmts_info_widget = (
        self.child_cls_name.lower() == objects.ASSESSMENTS)
    self.list_all_headers_txt = []
    self.list_all_values_txt = []
    self.info_widget_locator = (
        self._locators.INFO_PAGE_ELEM if self.is_info_page else
        self._locators.INFO_PANEL_ELEM)
    self.inline_edit_controls = self._browser.elements(
        class_name="set-editable-group")
    self.tabs = tab_element.Tabs(self._browser, tab_element.Tabs.INTERNAL)
    self._attributes_tab_name = "Attributes"
    self._changelog_tab_name = "Change Log"
    # for overridable methods
    if (self.__class__ in
        [Controls, Programs, Regulations, Objectives, Contracts,
         Policies, Risks, Standards, Threats, Requirements]):
      if self.is_info_page:
        self.tabs.ensure_tab(self._attributes_tab_name)
      self._extend_list_all_scopes_by_review_state()
    self.comment_area = self._comment_area()
    self.edit_popup = object_modal.get_modal_obj(self.obj_name, self._driver)

  @property
  def _root(self):
    """Returns root element (including title, 3bbs)."""
    if self.is_info_page:
      return self._browser.element(class_name="ggrc_controllers_info_widget")
    return self._browser.element(class_name="sticky-info-panel")

  @property
  def _active_tab_root(self):
    """Returns a wrapper el for active internal tab."""
    return self._root.element(class_name=["tab-pane", "active"])

  @property
  def info_widget_elem(self):
    """Returns info widget elem (obsolete).
    Use `self._root` or `self._active_tab_root` instead."""
    return selenium_utils.get_when_visible(
        self._driver, self.info_widget_locator)

  @property
  def panel(self):
    """Returns info panel."""
    if self.is_snapshot_panel:
      return info_panel.SnapshotInfoPanel(self._root)
    return info_panel.InfoPanel(self._root)

  @property
  def is_info_page(self):
    """Returns whether the page is info page."""
    return self.get_current_url_fragment() == self._url_fragment()

  @property
  def is_snapshot_panel(self):
    """Returns whether this page object represents snapshot Info Panel."""
    return info_panel.SnapshotInfoPanel(self._root).snapshot_version_el.present

  @staticmethod
  def _url_fragment():
    """See superclass."""
    return "info"

  def title(self):
    """Returns object title."""
    return self._browser.element(class_name="pane-header__title").h3().text

  def status(self):
    """Returns object status."""
    return self._browser.element(
        class_name=re.compile("state-value state")).text_content

  def code(self):
    """Returns code."""
    return self._simple_field("Code").text

  def created_at(self):
    """Return created date as shown in UI."""
    return self._extract_text_from_footer(1)

  def modified_by(self):
    """Return user that updated the object last."""
    return self._extract_text_from_footer(2)

  def updated_at(self):
    """Return last updated date."""
    return self._extract_text_from_footer(3)

  def _extract_text_from_footer(self, group_idx):
    """Returns some text part from footer."""
    footer_regexp = r"Created date (.+) {4}Last updated by\n(.+)\non (.+)"
    footer_el = self._browser.element(class_name="info-widget-footer")
    footer_el.element(class_name="person-name").wait_until_present()
    return re.search(footer_regexp, footer_el.text).group(group_idx)

  @staticmethod
  def wait_save():
    """Wait for object to be saved and page to be updated.
    Please note that in some cases spinner disappears before DOM changes
    are fully finished. So this code may need to be changed
    in case of a race condition.
    """
    ui_utils.wait_for_spinner_to_disappear()

  def get_review_state_txt(self):
    """Get object's review state text from Info Widget checking if exact UI
    elements are existed.
    """
    return (element.ReviewStates.REVIEWED if self._browser.element(
        class_name="state-reviewed") else element.ReviewStates.UNREVIEWED)

  def show_related_assessments(self):
    """Click `Assessments` button on control or objective page and return
    related asmts table.
    """
    self._browser.link(title="Show Related Assessments").click()
    table_element = self._driver.find_element(
        *locator.ModalRelatedAssessments.MODAL)
    return tables.AssessmentRelatedAsmtsTable(self._driver, table_element)

  @property
  def three_bbs(self):
    """Returns info widget three bbs element."""
    return self._dropdown_settings_cls(self._root)

  def get_header_and_value_txt_from_people_scopes(self, header_text):
    """Get with controlling header and value text from people's scopes elements
    according to header text.

    Example:
    'header_text' = 'ASSIGNEE(S)', return: ['ASSIGNEE(S)', 'user@example.com']
    """
    # pylint: disable=invalid-name
    # pylint: disable=expression-not-assigned
    _header_msg, _value_msg = (
        "people header: {}, count: {}", "people list: {}, count: {}")
    people_scopes = self._active_tab_root.locate().find_elements(
        *self._locators.PEOPLE_HEADERS_AND_VALUES_CSS)
    [selenium_utils.wait_until_stops_moving(people_scope)
     for people_scope in people_scopes]
    matched_people_scopes = [people_scope for people_scope in people_scopes
                             if header_text in people_scope.text]
    if len(matched_people_scopes) != 1:
      raise ValueError(
          messages.ExceptionsMessages.err_results_are_different.format(
              _header_msg.format(header_text, "1"),
              _value_msg.format(
                  [matched_people_scope.text
                   for matched_people_scope in matched_people_scopes],
                  len(matched_people_scopes))))
    people_scope = matched_people_scopes[0]
    _people_header = people_scope.find_element(
        *self._locators.PEOPLE_HEADER_CSS).text
    _people_value = people_scope.find_element(
        *self._locators.PEOPLE_VALUE_CSS).text
    # 'ASSIGNEE(S)\n(2)' to str 'ASSIGNEE(S)' and int '2'
    _people_header_parts = _people_header.splitlines()
    people_header_txt = _people_header_parts[0]
    people_count_from_header = (
        int(re.search(regex.TEXT_WO_PARENTHESES,
                      _people_header_parts[1]).group(1)))
    # filter: "\nuser@example.com\n(Inactive user)" to 'user@example.com'
    people_value_txt = [person for person in _people_value.splitlines()
                        if person != roles.NO_ROLE_UI]
    # if counters are same or None
    if not ((people_count_from_header == len(people_value_txt)) or
       (people_count_from_header == 0 and people_value_txt == ["None"])):
      raise ValueError(
          messages.ExceptionsMessages.err_counters_are_different.format(
              _header_msg.format(
                  _people_header_parts, str(people_count_from_header)),
              _value_msg.format(people_value_txt, len(people_value_txt))))
    return (people_header_txt,
            None if people_value_txt == ["None"] else people_value_txt)

  def description(self):
    """Returns the text of description."""
    return self._simple_field("Description").text

  @property
  def admins(self):
    """Returns Admin page element."""
    return self._related_people_list("Admin")

  def global_custom_attributes(self):
    """Returns GCA values."""
    return self.get_custom_attributes()

  def get_custom_attributes(self, is_gcas_not_lcas=True):
    """Get text of all CAs headers and values and convert it to dictionary.
    If 'is_gcas_not_lcas' then get GCAs, if not 'is_gcas_not_lcas'
    then get LCAs.
    Example:
    :return {'ca_header1': 'ca_value1', 'ca_header2': 'ca_value2', ...}
    """
    custom_attributes = {}
    ca_manager = page_elements.CustomAttributeManager(
        self._browser,
        obj_type=self.child_cls_name.lower(),
        is_global=is_gcas_not_lcas,
        is_inline=True)
    all_ca_titles = ca_manager.all_ca_titles()
    for ca_title in all_ca_titles:
      ca_elem = ca_manager.find_ca_elem_by_title(ca_title)
      custom_attributes[ca_title] = ca_elem.get_value()
    return custom_attributes

  def fill_global_cas_in_popup(self, custom_attributes):
    """Fills GCAs using Edit popup."""
    self.three_bbs.select_edit()
    self.fill_ca_values(custom_attributes, is_global=True, is_inline=False)

  def fill_global_cas_inline(self, custom_attributes):
    """Fills GCAs inline."""
    self.fill_ca_values(custom_attributes, is_global=True, is_inline=True)

  def fill_ca_values(self, custom_attributes, is_global, is_inline):
    """Fills custom attributes with values."""
    ca_manager = page_elements.CustomAttributeManager(
        self._browser,
        obj_type=self.child_cls_name.lower(),
        is_global=is_global,
        is_inline=is_inline)
    for attr_title, attr_value in custom_attributes.iteritems():
      elem_class = ca_manager.find_ca_elem_by_title(attr_title)
      elem_class.set_value(attr_value)
      if is_inline:
        self.wait_save()
    if not is_inline:
      self.edit_popup.save_and_close()

  def obj_scope(self):
    """Returns dict of object."""
    scope = {
        "description": self.description(),
        "custom_attributes": self.global_custom_attributes(),
        "url": self.get_url(),
        "id": self.get_obj_id(),
        "code": self.code(),
        "state": self.status(),
        "title": self.title()
    }
    if self.is_info_page:
      scope.update(
          created_at=self.created_at(),
          last_updated_by=self.modified_by(),
          updated_at=self.updated_at()
      )
    self.update_obj_scope(scope)
    return scope

  def update_obj_scope(self, scope):
    """Updates obj scope. May be overridden in the child class."""
    pass

  def get_info_widget_obj_scope(self):
    """Get dict from object (text scope) which displayed on info page or
    info panel according to list of headers text and list of values text.
    """
    obj_scope = self.obj_scope()
    obj_scope.update(zip(self.list_all_headers_txt, self.list_all_values_txt))
    return obj_scope

  def _extend_list_all_scopes(self, headers, values):
    """Extend 'list all scopes' by headers' text and values' text."""
    self.list_all_headers_txt.extend(help_utils.convert_to_list(headers))
    self.list_all_values_txt.extend(help_utils.convert_to_list(values))

  def _extend_list_all_scopes_by_review_state(self):
    """Set attributes related to 'review state' and extend
    'list all scopes' accordingly.
    """
    # pylint: disable=invalid-name
    self.review_state_lbl = self._browser.element(
        class_name="object-review__header-title")
    self.review_state_txt = self.get_review_state_txt()
    self._extend_list_all_scopes(
        self.review_state_lbl.text, self.review_state_txt)

  def changelog_validation_result(self):
    """Returns changelog validation result."""
    self.tabs.ensure_tab(self._changelog_tab_name)
    return tab_containers.changelog_tab_validate(
        self._browser.driver, self._active_tab_root.locate())


class Programs(WithObjectReview, InfoWidget):
  """Model for program object Info pages and Info panels."""
  # pylint: disable=too-many-instance-attributes
  _locators = locator.WidgetInfoProgram
  _elements = element.ProgramInfoWidget

  def __init__(self, driver):
    super(Programs, self).__init__(driver)
    self.manager, self.manager_entered = (
        self.get_header_and_value_txt_from_people_scopes(
            self._elements.PROGRAM_MANAGERS.upper()))
    self._extend_list_all_scopes(
        self.manager, self.manager_entered)
    self.reference_urls = self._related_urls(self._reference_url_label)

  def els_shown_for_editor(self):
    """Elements shown for user with edit permissions"""
    return [self.request_review_btn,
            self.three_bbs,
            self.comment_area.add_section,
            self.reference_urls.add_button] + list(self.inline_edit_controls)


class Workflow(InfoWidget):
  """Model for Workflow object Info pages and Info panels."""
  _locators = locator.WidgetInfoWorkflow

  def __init__(self, _driver=None):
    super(Workflow, self).__init__()

  def _extend_list_all_scopes_by_review_state(self):
    """Method overriding without action due to Workflows don't have
    'review states'.
    """
    pass

  def obj_scope(self):
    """Returns obj scope."""
    return {
        "obj_id": self.get_obj_id(),
        "title": self.title(),
        "status": self.status(),
        "description": self.description(),
        "admins": self.admins.get_people_emails(),
        "workflow_members": self.workflow_members.get_people_emails(),
        "code": self.code(),
        "created_at": self.created_at(),
        "modified_by": self.modified_by(),
        "updated_at": self.updated_at()
    }

  @property
  def workflow_members(self):
    """Returns Workflow Members page element."""
    return self._related_people_list("Workflow Member")


class CycleTask(InfoWidget):
  """Model for CycleTask object Info panel."""

  def obj_scope(self):
    """Returns obj scope."""
    return {
        "title": self.title(),
        "status": self.status(),
        "due_date": self.due_date
    }

  @property
  def due_date(self):
    """Returns Task Due Date."""
    return self._simple_field("Task Due date").text

  def click_map_objs(self):
    """Clicks `Map Objects` button."""
    self._browser.link(text="Map Objects").click()

  def mapped_objs(self):
    """Returns objects mapped to the cycle task."""
    # HACK: it's not possible to determine by looking at DOM whether
    #   the list of mapped objects was fully loaded or not.
    time.sleep(1)
    objs = []
    row_els = self._browser.element(text="Mapped objects").next_sibling().lis()
    for obj_row in row_els:
      obj_id = int(obj_row.data_id)
      entity_obj_name = obj_row.data_object_type
      obj_title = obj_row.text
      factory = app_entity_factory.get_factory_by_obj_name(entity_obj_name)()
      objs.append(factory.create_empty(obj_id=obj_id, title=obj_title))
    return objs


class Audits(WithAssignFolder, InfoWidget):
  """Model for Audit object Info pages and Info panels."""
  # pylint: disable=too-many-instance-attributes
  _locators = locator.WidgetInfoAudit
  _elements = element.AuditInfoWidget
  _dropdown_settings_cls = info_widget_three_bbs.AuditInfoWidgetThreeBbbs

  def __init__(self, driver):
    super(Audits, self).__init__(driver)
    self.audit_captain_lbl_txt, self.audit_captain_txt = (
        self.get_header_and_value_txt_from_people_scopes(
            self._elements.AUDIT_CAPTAINS.upper()))
    self.auditor_lbl_txt, self.auditor_txt = (
        self.get_header_and_value_txt_from_people_scopes(
            self._elements.AUDITORS.upper()))
    self._extend_list_all_scopes(
        [self.audit_captain_lbl_txt, self.auditor_lbl_txt],
        [self.audit_captain_txt, self.auditor_txt])
    self.evidence_urls = self._related_urls(self._evidence_url_label)

  def _extend_list_all_scopes_by_review_state(self):
    """Method overriding without action due to Audits don't have
    'review states'.
    """
    pass

  def els_shown_for_editor(self):
    """Elements shown for user with edit permissions"""
    return [self.evidence_urls.add_button,
            self.assign_folder_button] + list(self.inline_edit_controls)


class Assessments(InfoWidget):
  """Model for Assessment object Info pages and Info panels."""
  # pylint: disable=invalid-name
  # pylint: disable=too-many-instance-attributes
  # pylint: disable=too-many-public-methods
  _locators = locator.WidgetInfoAssessment
  _elements = element.AssessmentInfoWidget
  _dropdown_settings_cls = info_widget_three_bbs.AssessmentInfoWidgetThreeBbbs

  def __init__(self, driver):
    super(Assessments, self).__init__(driver)
    self._assessment_tab_name = "Assessment"
    self._related_assessments_tab_name = "Related Assessments"
    self._related_issues_tab_name = "Related Issues"
    self._other_attributes_tab_name = "Other Attributes"

  def update_obj_scope(self, scope):
    """Updates obj scope."""
    scope.update(
        is_verified=self.is_verified,
        assessment_type=self.assessment_type,
        evidence_urls=self.evidence_urls.get_urls(),
        creators=self.creators.get_people_emails(),
        assignees=self.assignees.get_people_emails(),
        verifiers=self.verifiers.get_people_emails(),
        comments=self.comments_panel.scopes,
        custom_attributes=self.custom_attributes(),
        primary_contacts=self.primary_contacts.get_people_emails(),
        mapped_objects=self.mapped_objects_titles()
    )

  @property
  def is_verified(self):
    """Returns whether assessment is verified (has verified icon)."""
    self.tabs.ensure_tab(self._assessment_tab_name)
    return self._browser.element(class_name="verified-icon").exists

  @property
  def assessment_type(self):
    """Returns Assessment type."""
    self.tabs.ensure_tab(self._assessment_tab_name)
    return objects.get_singular(self._browser.element(
        class_name="action-toolbar__content-item").text, title=True)

  @property
  def evidence_urls(self):
    """Switch to tab with evidence urls and return a page element"""
    self.tabs.ensure_tab(self._assessment_tab_name)
    return self._assessment_evidence_urls()

  @property
  def creators(self):
    """Switch to tab with creators and return a page element."""
    self.tabs.ensure_tab(self._assessment_tab_name)
    return self._related_people_list("Creators")

  @property
  def assignees(self):
    """Switch to tab with assignees and return a page element."""
    self.tabs.ensure_tab(self._assessment_tab_name)
    return self._related_people_list("Assignees")

  @property
  def verifiers(self):
    """Switch to tab with verifiers and return a page element."""
    self.tabs.ensure_tab(self._assessment_tab_name)
    return self._related_people_list("Verifiers")

  @property
  def comments_panel(self):
    """Returns comments panel."""
    self.tabs.ensure_tab(self._assessment_tab_name)
    return base.CommentsPanel(
        self._root.locate(), self._locators.COMMENTS_CSS)

  def description(self):
    """Switch to tab with description and return a text of description."""
    self.tabs.ensure_tab(self._other_attributes_tab_name)
    return self._assessment_form_field("Description").text

  def code(self):
    """Switch to tab with code and return the text of code."""
    self.tabs.ensure_tab(self._other_attributes_tab_name)
    return self._info_pane_form_field("Code").text

  @property
  def primary_contacts(self):
    """Switch to tab with primary contacts and return a page element"""
    self.tabs.ensure_tab(self._other_attributes_tab_name)
    return self._related_people_list("Primary Contacts")

  def mapped_objects_titles(self):
    """Returns list of mapped snapshots' titles."""
    def titles_from_current_tab():
      """Returns list of mapped snapshots' titles on current tab."""
      els = self._active_tab_root.elements(class_name="mapped-snapshot-item")
      return [el.element(class_name="title").text for el in els]
    self.tabs.ensure_tab(self._assessment_tab_name)
    titles = titles_from_current_tab()
    self.tabs.ensure_tab(self._other_attributes_tab_name)
    return titles + titles_from_current_tab()

  def custom_attributes(self):
    """Returns the dictionary of all custom attributes."""
    custom_attributes = self.global_custom_attributes()
    custom_attributes.update(self.local_custom_attributes())
    return custom_attributes

  def global_custom_attributes(self):
    """Switches to tab with GCA and returns their values."""
    self.tabs.ensure_tab(self._other_attributes_tab_name)
    return self.get_custom_attributes()

  def local_custom_attributes(self):
    """Switches to tab with LCA and returns their values."""
    self.tabs.ensure_tab(self._assessment_tab_name)
    custom_attributes = self.get_custom_attributes(False)
    return {k.upper(): v for k, v in custom_attributes.iteritems()}

  def fill_local_cas(self, custom_attributes):
    """Fills LCAs on asmt page."""
    self.tabs.ensure_tab(self._assessment_tab_name)
    self.fill_ca_values(custom_attributes, is_global=False, is_inline=True)

  @property
  def related_assessments_table(self):
    """Switches to Related Assessments tab
    and returns AssessmentRelatedAsmtsTable.
    """
    self.tabs.ensure_tab(self._related_assessments_tab_name)
    return tables.AssessmentRelatedAsmtsTable(
        self._browser.driver, self._active_tab_root.locate())

  @property
  def related_issues_table(self):
    """Switches to Related Issues tab and returns RelatedIssuesTable."""
    self.tabs.ensure_tab(self._related_issues_tab_name)
    return tables.AssessmentRelatedIssuesTable(
        self._browser.driver, self._active_tab_root.locate())

  def fill_global_cas_inline(self, custom_attributes):
    """Fills GCAs inline."""
    self.tabs.ensure_tab(self._other_attributes_tab_name)
    self.fill_ca_values(custom_attributes, is_global=True, is_inline=True)

  def _extend_list_all_scopes_by_review_state(self):
    """Method overriding without action due to Assessments don't have
    'review states'.
    """
    pass

  def click_complete(self):
    """Click on 'Complete' button."""
    base.Button(self.info_widget_elem,
                WidgetInfoAssessment.BUTTON_COMPLETE).click()

  def click_verify(self):
    """Click on 'Verify' button."""
    base.Button(self.info_widget_elem,
                WidgetInfoAssessment.BUTTON_VERIFY).click()

  def click_needs_rework(self):
    """Click on 'Needs Rework' button."""
    base.Button(self.info_widget_elem,
                WidgetInfoAssessment.BUTTON_NEEDS_REWORK).click()

  def choose_and_fill_dropdown_lca(self, dropdown_id, option_title, **kwargs):
    """Choose and fill comment or url for Assessment dropdown."""
    self.select_ca_dropdown_option(dropdown_id, option_title)
    SetValueForAsmtDropdown(self._driver).fill_dropdown_lca(**kwargs)
    selenium_utils.get_when_clickable(
        self._driver, WidgetInfoAssessment.BUTTON_COMPLETE)

  def select_ca_dropdown_option(self, dropdown_id, option_value):
    """Select custom attribute dropdown option."""
    dropdown_locator = (
        By.CSS_SELECTOR, "#form-field-{}".format(dropdown_id))
    selenium_utils.get_when_clickable(
        self.info_widget_elem, dropdown_locator)
    base.DropdownStatic(self.info_widget_elem,
                        dropdown_locator).select(option_value)

  def edit_answers(self):
    """Click to Edit Answers and Confirm"""
    self._browser.button(text="Edit Answers").click()
    self._browser.element(class_name="modal").link(text="Confirm").click()
    self.wait_save()


class AssessmentTemplates(InfoWidget):
  """Model for Assessment Template object Info pages and Info panels."""
  _locators = locator.WidgetInfoAssessmentTemplate

  def __init__(self, driver):
    super(AssessmentTemplates, self).__init__(driver)

  def _extend_list_all_scopes_by_review_state(self):
    """Method overriding without action due to Assessment Templates don't have
    'review states'.
    """
    pass


class Issues(InfoWidget):
  """Model for Issue object Info pages and Info panels."""
  _locators = locator.WidgetInfoIssue
  _elements = element.IssueInfoWidget

  def __init__(self, driver):
    super(Issues, self).__init__(driver)


class Regulations(InfoWidget):
  """Model for Assessment object Info pages and Info panels."""
  _locators = locator.WidgetInfoRegulations

  def __init__(self, driver):
    super(Regulations, self).__init__(driver)


class Policies(InfoWidget):
  """Model for Policy object Info pages and Info panels."""
  _locators = locator.WidgetInfoPolicy

  def __init__(self, driver):
    super(Policies, self).__init__(driver)


class Standards(InfoWidget):
  """Model for Standard object Info pages and Info panels."""
  _locators = locator.WidgetInfoStandard

  def __init__(self, driver):
    super(Standards, self).__init__(driver)


class Contracts(InfoWidget):
  """Model for Contract object Info pages and Info panels."""
  _locators = locator.WidgetInfoContract

  def __init__(self, driver):
    super(Contracts, self).__init__(driver)


class Requirements(InfoWidget):
  """Model for Requirement object Info pages and Info panels."""
  _locators = locator.WidgetInfoRequirement

  def __init__(self, driver):
    super(Requirements, self).__init__(driver)


class Controls(WithAssignFolder, WithObjectReview, InfoWidget):
  """Model for Control object Info pages and Info panels."""
  # pylint: disable=too-many-instance-attributes
  _locators = locator.WidgetInfoControl
  _elements = element.ControlInfoWidget

  def __init__(self, driver):
    super(Controls, self).__init__(driver)
    self.admin_text, self.admin_entered_text = (
        self.get_header_and_value_txt_from_people_scopes(
            self._elements.ADMIN.upper()))
    self.primary_contact_text, self.primary_contact_entered_text = (
        self.get_header_and_value_txt_from_people_scopes(
            self._elements.PRIMARY_CONTACTS.upper()))
    self._assertions = self._browser.element(
        class_name="custom-attr-wrap").element(
        text="Assertions").parent().text.splitlines()
    self.assertions_text = self._assertions[0]
    self.assertions_entered_text = self._assertions[1:]
    self.reference_urls = self._related_urls(self._reference_url_label)
    self._extend_list_all_scopes(
        [self.admin_text, self.primary_contact_text, self.assertions_text],
        [self.admin_entered_text, self.primary_contact_entered_text,
         self.assertions_entered_text])
    self._add_obj_review_to_lsopes()
    self.proposals_tab = "Change Proposals"

  def _add_obj_review_to_lsopes(self):
    """Extend list of scopes by object review section """
    review_msg = None
    approved_el = self._browser.element(class_name="state-reviewed")
    if approved_el.present:
      review_msg = self._browser.element(class_name="object-review__body").text
    self._extend_list_all_scopes(self._elements.OBJECT_REVIEW_FULL, review_msg)

  def open_submit_for_review_popup(self):
    """Open submit for control popub by clicking on corresponding button."""
    self._browser.button(text="Request Review").click()
    selenium_utils.wait_for_js_to_load(self._driver)

  def select_assignee_user(self, user_email):
    """Select assignee user from dropdown on submit for review popup."""
    self._browser.text_field(placeholder="Add person").set(user_email)
    ui_utils.select_user(self._browser, user_email)

  def select_first_available_date(self):
    """Select first available day on datepicker on submit for review popup."""
    date_picker = base.DatePicker(self._driver,
                                  WidgetInfoControl.DATE_PICKER_FIELD,
                                  WidgetInfoControl.DATE_PICKER_LOCATOR)
    date_picker.select_month_start()

  def click_request(self):
    """Click request."""
    self._browser.element(
        xpath="//div[@class='simple-modal request-review-modal']"
              "//button[contains(., 'Request')]").click()
    selenium_utils.wait_for_js_to_load(self._driver)

  def click_approve_review(self):
    """Click approve review button."""
    self._browser.element(text="Mark Reviewed").click()

  def leave_request_review_comment(self, comment_msg):
    """Leave request review comment."""
    comments_elem = self._browser.element(
        xpath="//div[@class='simple-modal request-review-modal']"
              "//div[@data-placeholder='Enter comment']")
    comments_elem.click()
    comments_elem.send_keys(comment_msg)

  def click_propose_changes(self):
    """Click on Propose Changes button."""
    self._browser.element(tag_name="create-proposal-button").link().click()

  def els_shown_for_editor(self):
    """Elements shown for user with edit permissions"""
    return [self.request_review_btn,
            self.three_bbs,
            self.comment_area.add_section,
            self.reference_urls.add_button,
            self.assign_folder_button] + list(self.inline_edit_controls)

  def related_proposals(self):
    """Open related proposals tab."""
    self.tabs.ensure_tab(self.proposals_tab)
    selenium_utils.wait_for_js_to_load(self._driver)
    return related_proposals.RelatedProposals()


class Objectives(InfoWidget):
  """Model for Objective object Info pages and Info panels."""
  _locators = locator.WidgetInfoObjective

  def __init__(self, driver):
    super(Objectives, self).__init__(driver)


class OrgGroups(InfoWidget):
  """Model for Org Group object Info pages and Info panels."""
  _locators = locator.WidgetInfoOrgGroup

  def __init__(self, driver):
    super(OrgGroups, self).__init__(driver)

  def update_obj_scope(self, scope):
    """Updates obj scope."""
    scope.update(
        admin=self.admins.get_people_emails()
    )


class Vendors(InfoWidget):
  """Model for Vendor object Info pages and Info panels."""
  _locators = locator.WidgetInfoVendor

  def __init__(self, driver):
    super(Vendors, self).__init__(driver)


class AccessGroup(InfoWidget):
  """Model for Access Group object Info pages and Info panels."""
  _locators = locator.WidgetInfoAccessGroup

  def __init__(self, driver):
    super(AccessGroup, self).__init__(driver)


class Systems(InfoWidget):
  """Model for System object Info pages and Info panels."""
  _locators = locator.WidgetInfoSystem

  def __init__(self, driver):
    super(Systems, self).__init__(driver)


class Processes(InfoWidget):
  """Model for Process object Info pages and Info panels."""
  _locators = locator.WidgetInfoProcess

  def __init__(self, driver):
    super(Processes, self).__init__(driver)


class DataAssets(InfoWidget):
  """Model for Data Asset object Info pages and Info panels."""
  _locators = locator.WidgetInfoDataAsset

  def __init__(self, driver):
    super(DataAssets, self).__init__(driver)


class Products(InfoWidget):
  """Model for Product object Info pages and Info panels."""
  _locators = locator.WidgetInfoProduct

  def __init__(self, driver):
    super(Products, self).__init__(driver)


class Projects(InfoWidget):
  """Model for Project object Info pages and Info panels."""
  _locators = locator.WidgetInfoProject

  def __init__(self, driver):
    super(Projects, self).__init__(driver)


class Facilities(InfoWidget):
  """Model for Facility object Info pages and Info panels."""
  _locators = locator.WidgetInfoFacility

  def __init__(self, driver):
    super(Facilities, self).__init__(driver)


class Markets(InfoWidget):
  """Model for Market object Info pages and Info panels."""
  _locators = locator.WidgetInfoMarket

  def __init__(self, driver):
    super(Markets, self).__init__(driver)


class Risks(InfoWidget):
  """Model for Risk object Info pages and Info panels."""
  _locators = locator.WidgetInfoRisk

  def __init__(self, driver):
    super(Risks, self).__init__(driver)

  def update_obj_scope(self, scope):
    """Updates obj scope."""
    scope.update(
        admin=self.admins.get_people_emails()
    )


class Threats(InfoWidget):
  """Model for Threat object Info pages and Info panels."""
  _locators = locator.WidgetInfoThreat

  def __init__(self, driver):
    super(Threats, self).__init__(driver)


class People(base.Widget):
  """Model for People object Info pages and Info panels."""
  # pylint: disable=too-few-public-methods
  _locators = locator.WidgetInfoPeople


class Dashboard(base.Widget):
  """Model for Dashboard object Info pages and Info panels."""
  # pylint: disable=too-few-public-methods

  _locators = locator.Dashboard

  def __init__(self, driver):
    super(Dashboard, self).__init__(driver)
    self.start_new_program_btn = base.Button(
        self._driver, self._locators.START_NEW_PROGRAM_BTN_CSS)
    self.start_new_audit_btn = base.Button(
        self._driver, self._locators.START_NEW_AUDIT_BTN_CSS)
    self.start_new_workflow_btn = base.Button(
        self._driver, self._locators.START_NEW_WORKFLOW_BTN_CSS)
    self.create_task_btn = base.Button(
        self._driver, self._locators.CREATE_TASK_BTN_CSS)
    self.create_object_btn = base.Button(
        self._driver, self._locators.CREATE_OBJECT_BTN_CSS)
    self.all_objects_btn = base.Button(
        self._driver, self._locators.ALL_OBJECTS_BTN_CSS)
