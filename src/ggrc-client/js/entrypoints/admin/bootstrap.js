/*
    Copyright (C) 2018 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import {
  initWidgets,
} from '../../plugins/utils/widgets-utils';
import '../../controllers/dashboard_controller';
import {RouterConfig} from '../../router';
import routes from './routes';
import {gapiClient} from '../../plugins/ggrc-gapi-client';
import Event from '../../models/service-models/event';
import Role from '../../models/service-models/role';
import CustomAttributable from '../../models/custom-attributes/custom-attributable';
import CustomAttributeDefinition from '../../models/custom-attributes/custom-attribute-definition';
import AccessControlRole from '../../models/custom-roles/access-control-role';
import Roleable from '../../models/custom-roles/roleable';
import Person from '../../models/business-models/person';
import WidgetList from '../../modules/widget_list';

const path = GGRC.mustache_path || '/static/mustache';
const HEADER_VIEW = `${path}/base_objects/page_header.mustache`;

const $area = $('.area').first();
const sortByNameEmail = list => {
  return new list.constructor(can.makeArray(list).sort(function (a, b) {
    a = a.person || a;
    b = b.person || b;
    a = (can.trim(a.name) || can.trim(a.email)).toLowerCase();
    b = (can.trim(b.name) || can.trim(b.email)).toLowerCase();
    if (a > b) {
      return 1;
    }
    if (a < b) {
      return -1;
    }
    return 0;
  }));
};

RouterConfig.setupRoutes(routes);
gapiClient.loadGapiClient();

const adminListDescriptors = {
  people: {
    model: Person,
    roles: new can.List(),
    init: function () {
      let self = this;
      Role
        .findAll({scope__in: 'System,Admin'})
        .done(function (roles) {
          self.roles.replace(sortByNameEmail(roles));
        });
    },
    object_display: 'People',
    tooltip_view: '/static/mustache/people/object_tooltip.mustache',
    header_view:
    // includes only the filter, not the column headers
      '/static/mustache/people/filters.mustache',
    list_view: '/static/mustache/people/object_list.mustache',
    draw_children: true,
    fetch_post_process: sortByNameEmail,
  },
  roles: {
    model: Role,
    extra_params: {scope__in: 'System,Admin,Private Program,Workflow'},
    object_category: 'governance',
    object_display: 'Roles',
    list_view: '/static/mustache/roles/object_list.mustache',
    fetch_post_process: sortByNameEmail,
  },
  events: {
    model: Event,
    object_category: 'governance',
    object_display: 'Events',
    list_view: '/static/mustache/events/object_list.mustache',
  },
  custom_attributes: {
    parent_instance: CustomAttributable,
    model: CustomAttributable,
    header_view:
    GGRC.mustache_path +
    '/custom_attribute_definitions/tree_header.mustache',
    show_view:
    GGRC.mustache_path + '/custom_attribute_definitions/tree.mustache',
    sortable: false,
    list_loader: function () {
      return CustomAttributable.findAll();
    },
    draw_children: true,
    child_options: [{
      model: CustomAttributeDefinition,
      mapping: 'custom_attribute_definitions',
      show_view:
      GGRC.mustache_path +
      '/custom_attribute_definitions/subtree.mustache',
      add_item_view: null,
    }],
  },
  custom_roles: {
    parent_instance: Roleable,
    model: Roleable,
    header_view:
    GGRC.mustache_path + '/access_control_roles/tree_header.mustache',
    show_view:
    GGRC.mustache_path + '/access_control_roles/tree.mustache',
    sortable: false,
    list_loader: function () {
      return Roleable.findAll();
    },
    draw_children: true,
    child_options: [{
      model: AccessControlRole,
      mapping: 'access_control_roles',
      show_view:
      GGRC.mustache_path + '/access_control_roles/subtree.mustache',
      add_item_view: null,
    }],
  },
};

new WidgetList('ggrc_admin', {
  admin: {
    people: {
      model: Person,
      content_controller: GGRC.Controllers.ListView,
      content_controller_options: adminListDescriptors.people,
      widget_id: 'people_list',
      widget_icon: 'person',
      show_filter: false,
      widget_name: function () {
        return 'People';
      },
      widget_info: function () {
        return '';
      },
    },
    roles: {
      model: Role,
      content_controller: GGRC.Controllers.ListView,
      content_controller_options: adminListDescriptors.roles,
      widget_id: 'roles_list',
      widget_icon: 'role',
      show_filter: false,
      widget_name: function () {
        return 'Roles';
      },
      widget_info: function () {
        return '';
      },
    },
    events: {
      model: Event,
      content_controller: GGRC.Controllers.ListView,
      content_controller_options: adminListDescriptors.events,
      widget_id: 'events_list',
      widget_icon: 'event',
      widget_name: function () {
        return 'Events';
      },
      widget_info: function () {
        return '';
      },
    },
    custom_attributes: {
      widget_id: 'custom_attribute',
      widget_name: 'Custom Attributes',
      widget_icon: 'workflow',
      content_controller: CMS.Controllers.TreeView,
      content_controller_selector: 'ul',
      model: CustomAttributable,
      widget_initial_content:
      '<ul' +
      '  class="tree-structure new-tree colored-list"' +
      '  data-no-pin="true"' +
      '></ul>',
      content_controller_options: adminListDescriptors.custom_attributes,
    },
    custom_roles: {
      widget_id: 'custom_roles',
      widget_name: 'Custom Roles',
      widget_icon: 'unlock',
      content_controller: CMS.Controllers.TreeView,
      content_controller_selector: 'ul',
      content_controller_options: adminListDescriptors.custom_roles,
      model: Roleable,
      widget_initial_content: [
        '<ul',
        '  class="tree-structure new-tree colored-list"',
        '  data-no-pin="true"',
        '></ul>',
      ].join('\n'),
    },
  },
});

$area.cms_controllers_dashboard({
  widget_descriptors: WidgetList.get_widget_list_for('admin'),
  menu_tree_spec: GGRC.admin_menu_spec,
  header_view: HEADER_VIEW,
  default_widgets: [
    'people', 'roles', 'events', 'custom_attributes', 'custom_roles',
  ],
});
initWidgets();
