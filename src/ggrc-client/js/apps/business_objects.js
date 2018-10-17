/*
    Copyright (C) 2018 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import SummaryWidgetController from '../controllers/summary_widget_controller';
import DashboardWidget from '../controllers/dashboard_widget_controller';
import InfoWidget from '../controllers/info_widget_controller';
import WidgetList from '../modules/widget_list';
import {isDashboardEnabled} from '../plugins/utils/dashboards-utils';
import {
  getWidgetConfig,
} from '../plugins/utils/object-versions-utils';
import {widgetModules} from '../plugins/utils/widgets-utils';
import {
  getPageInstance,
  getPageModel,
} from '../plugins/utils/current-page-utils';
import * as businessModels from '../models/business-models/index';

let CoreExtension = {};

CoreExtension.name = 'core"';
widgetModules.push(CoreExtension);
_.assign(CoreExtension, {
  init_widgets: function () {
    let baseWidgetsByType = GGRC.tree_view.base_widgets_by_type;
    let widgetList = new WidgetList('ggrc_core');
    let objectClass = getPageModel();
    let objectTable = objectClass && objectClass.table_plural;
    let object = getPageInstance();
    let path = GGRC.mustache_path;
    let infoWidgetViews;
    let summaryWidgetViews;
    let modelNames;
    let possibleModelType;
    let farModels;
    let extraDescriptorOptions;
    let extraContentOptions;

    // Info and summary widgets display the object information instead of listing
    // connected objects.
    summaryWidgetViews = {
      audits: path + '/audits/summary.mustache',
    };
    if (summaryWidgetViews[objectTable]) {
      widgetList.add_widget(object.constructor.shortName, 'summary', {
        widget_id: 'summary',
        content_controller: SummaryWidgetController,
        instance: object,
        widget_view: summaryWidgetViews[objectTable],
        order: 3,
        uncountable: true,
      });
    }
    if (isDashboardEnabled(object)) {
      widgetList.add_widget(object.constructor.shortName, 'dashboard', {
        widget_id: 'dashboard',
        content_controller: DashboardWidget,
        instance: object,
        widget_view: path + '/base_objects/dashboard_widget.mustache',
        order: 6,
        uncountable: true,
      });
    }
    infoWidgetViews = {
      programs: path + '/programs/info.mustache',
      audits: path + '/audits/info.mustache',
      people: path + '/people/info.mustache',
      policies: path + '/policies/info.mustache',
      controls: path + '/controls/info.mustache',
      systems: path + '/systems/info.mustache',
      processes: path + '/processes/info.mustache',
      products: path + '/products/info.mustache',
      assessments: path + '/assessments/info.mustache',
      assessment_templates:
        path + '/assessment_templates/info.mustache',
      issues: path + '/issues/info.mustache',
      evidence: path + '/evidence/info.mustache',
      documents: path + '/documents/info.mustache',
      risks: path + '/risks/info.mustache',
    };
    widgetList.add_widget(object.constructor.shortName, 'info', {
      widget_id: 'info',
      content_controller: InfoWidget,
      instance: object,
      widget_view: infoWidgetViews[objectTable],
      order: 5,
      uncountable: true,
    });
    modelNames = can.Map.keys(baseWidgetsByType);
    modelNames.sort();
    possibleModelType = modelNames.slice();
    can.each(modelNames, function (name) {
      let wList;
      let childModelList = [];
      let widgetConfig = getWidgetConfig(name);
      name = widgetConfig.name;
      GGRC.tree_view.basic_model_list.push({
        model_name: name,
        display_name: widgetConfig.widgetName,
      });

      // Initialize child_model_list, and child_display_list each model_type
      wList = baseWidgetsByType[name];

      can.each(wList, function (item) {
        let childConfig;
        if (possibleModelType.indexOf(item) !== -1) {
          childConfig = getWidgetConfig(name);
          childModelList.push({
            model_name: childConfig.name,
            display_name: childConfig.widgetName,
          });
        }
      });
      GGRC.tree_view.sub_tree_for.attr(name, {
        model_list: childModelList,
        display_list: businessModels[name]
          .tree_view_options.child_tree_display_list || wList,
      });
    });

    function applyMixins(definitions) {
      let mappings = {};

      // Recursively handle mixins
      function reifyMixins(definition) {
        let finalDefinition = {};
        if (definition._mixins) {
          can.each(definition._mixins, function (mixin) {
            if (typeof (mixin) === 'string') {
              // If string, recursive lookup
              if (!definitions[mixin]) {
                console.warn(`Undefined mixin: ${mixin} ${definitions}`);
              } else {
                can.extend(
                  finalDefinition,
                  reifyMixins(definitions[mixin])
                );
              }
            } else if (can.isFunction(mixin)) {
              // If function, call with current definition state
              mixin(finalDefinition);
            } else {
              // Otherwise, assume object and extend
              can.extend(finalDefinition, mixin);
            }
          });
        }
        can.extend(finalDefinition, definition);
        delete finalDefinition._mixins;
        return finalDefinition;
      }

      can.each(definitions, function (definition, name) {
        // Only output the mappings if it's a model, e.g., uppercase first letter
        if (name[0] === name[0].toUpperCase()) {
          mappings[name] = reifyMixins(definition);
        }
      });

      return mappings;
    }

    // the assessments_view only needs the Assessments widget
    if (/^\/assessments_view/.test(window.location.pathname)) {
      farModels = ['Assessment'];
    } else {
      farModels = baseWidgetsByType[object.constructor.shortName];
    }

    // here we are going to define extra descriptor options, meaning that
    //  these will be used as extra options to create widgets on top of

    extraDescriptorOptions = {
      all: (function () {
        let all = {
          Evidence: {
            treeViewDepth: 0,
          },
          AssessmentTemplate: {
            treeViewDepth: 0,
          },
          Person: {
            widget_icon: 'person',
          },
        };

        let defOrder = GGRC.tree_view.attr('defaultOrderTypes');
        Object.keys(defOrder).forEach(function (type) {
          if (!all[type]) {
            all[type] = {};
          }
          all[type].order = defOrder[type];
        });

        return all;
      })(),
      Program: {
        Person: {
          widget_id: 'person',
          widget_name: 'People',
          widget_icon: 'person',
        },
      },

      // An Audit has a different set of object that are more relevant to it,
      // thus these objects have a customized priority. On the other hand,
      // the object otherwise prioritized by default (e.g. Regulation) have
      // their priority lowered so that they fit nicely into the alphabetical
      // order among the non-prioritized object types.
      Audit: {
        Assessment: {
          order: 7,
        },
        Issue: {
          order: 8,
        },
        Evidence: {
          order: 9,
        },
        program: {
          widget_id: 'program',
          widget_name: 'Program',
          widget_icon: 'program',
        },
        Person: {
          widget_id: 'person',
          widget_name: 'People',
          widget_icon: 'person',
          // NOTE: "order" not overridden
          content_controller_options: {
            allow_mapping: false,
            allow_creating: false,
          },
        },
      },
    };

    extraContentOptions = applyMixins({
      objectives: {
        Objective: {
          draw_children: true,
          add_item_view: path + '/snapshots/tree_add_item.mustache',
        },
      },
      controls: {
        Control: {
          draw_children: true,
          add_item_view: path + '/snapshots/tree_add_item.mustache',
        },
      },
      business_objects: {
        Audit: {
          draw_children: true,
          allow_mapping: true,
          add_item_view: path + '/audits/tree_add_item.mustache',
        },
        AccessGroup: {
          draw_children: true,
        },
        DataAsset: {
          draw_children: true,
        },
        Facility: {
          draw_children: true,
        },
        Market: {
          draw_children: true,
        },
        Metric: {
          draw_children: true,
        },
        OrgGroup: {
          draw_children: true,
        },
        Vendor: {
          draw_children: true,
        },
        Process: {
          draw_children: true,
        },
        Product: {
          draw_children: true,
        },
        ProductGroup: {
          draw_children: true,
        },
        Project: {
          draw_children: true,
        },
        System: {
          draw_children: true,
        },
        Assessment: {
          draw_children: true,
        },
        Person: {
          draw_children: true,
        },
        Program: {
          draw_children: true,
        },
        Risk: {
          draw_children: true,
        },
        TechnologyEnvironment: {
          draw_children: true,
        },
        Threat: {
          draw_children: true,
        },
      },
      issues: {
        Issue: {
          draw_children: true,
        },
      },
      governance_objects: {
        Regulation: {
          draw_children: true,
          add_item_view: path + '/snapshots/tree_add_item.mustache',
        },
        Contract: {
          draw_children: true,
        },
        Policy: {
          draw_children: true,
          add_item_view: path + '/snapshots/tree_add_item.mustache',
        },
        Standard: {
          draw_children: true,
          add_item_view: path + '/snapshots/tree_add_item.mustache',
        },
        Control: {
          draw_children: true,
        },
        Objective: {
          draw_children: true,
        },
        Requirement: {
          draw_children: true,
        },
      },
      Program: {
        _mixins: [
          'governance_objects', 'objectives', 'controls',
          'business_objects', 'issues',
        ],
        Audit: {
          allow_mapping: true,
          draw_children: true,
          add_item_view: path + '/audits/tree_add_item.mustache',
        },
        Person: {
          parent_instance: getPageInstance(),
          allow_reading: true,
          allow_mapping: true,
          allow_creating: true,
          model: businessModels.Person,
          draw_children: true,
        },
      },
      Audit: {
        _mixins: ['issues', 'governance_objects', 'business_objects'],
        Program: {
          parent_instance: getPageInstance(),
          draw_children: true,
          model: businessModels.Program,
          allow_mapping: false,
          allow_creating: false,
        },
        Requirement: {
          draw_children: true,
        },
        Threat: {
          draw_children: true,
        },
        Risk: {
          draw_children: true,
        },
        Assessment: {
          parent_instance: getPageInstance(),
          allow_mapping: true,
          draw_children: true,
          model: businessModels.Assessment,
          add_item_view: path + '/assessments/tree_add_item.mustache',
        },
        AssessmentTemplate: {
          draw_children: false,
          allow_mapping: false,
          add_item_view: GGRC.mustache_path +
            '/assessment_templates/tree_add_item.mustache',
        },
        Person: {
          widget_id: 'person',
          widget_name: 'People',
          widget_icon: 'person',
          draw_children: true,
          content_controller_options: {
            allow_mapping: false,
            allow_creating: false,
          },
        },
      },
      directive: {
        _mixins: [
          'objectives', 'controls', 'business_objects',
        ],
        Requirement: {
          draw_children: true,
        },
        Audit: {
          draw_children: true,
        },
      },
      Regulation: {
        _mixins: ['directive', 'issues'],
      },
      Standard: {
        _mixins: ['directive', 'issues'],
      },
      Policy: {
        _mixins: ['directive', 'issues'],
      },
      Contract: {
        _mixins: ['directive', 'issues'],
      },
      Requirement: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
        Audit: {
          draw_children: true,
        },
      },
      Objective: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
        Audit: {
          draw_children: true,
        },
      },
      Control: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
        Audit: {
          draw_children: true,
        },
      },
      Assessment: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
        Audit: {
          draw_children: true,
          allow_creating: false,
          allow_mapping: true,
          add_item_view: path + '/audits/tree_add_item.mustache',
        },
        Requirement: {
          draw_children: true,
        },
      },
      AssessmentTemplate: {
        Audit: {
          draw_children: true,
          allow_creating: false,
          allow_mapping: true,
        },
      },
      Risk: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
        Threat: {
          draw_children: true,
        },
      },
      Threat: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
        Risk: {
          draw_children: true,
        },
      },
      Issue: {
        _mixins: ['governance_objects', 'business_objects'],
        Control: {
          draw_children: true,
          add_item_view: path + '/base_objects/tree_add_item.mustache',
        },
        Audit: {
          draw_children: true,
          add_item_view:
            GGRC.mustache_path + '/base_objects/tree_add_item.mustache',
        },
      },
      AccessGroup: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      DataAsset: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      Facility: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      Market: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      Metric: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      OrgGroup: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      Vendor: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      Process: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      Product: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      ProductGroup: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      Project: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      System: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      TechnologyEnvironment: {
        _mixins: ['governance_objects', 'business_objects', 'issues'],
      },
      Person: {
        _mixins: ['issues'],
        Program: {
          draw_children: true,
        },
        Regulation: {
          draw_children: true,
        },
        Contract: {
          draw_children: true,
        },
        Standard: {
          draw_children: true,
        },
        Policy: {
          draw_children: true,
        },
        Audit: {
          draw_children: true,
        },
        Requirement: {
          add_item_view:
            GGRC.mustache_path + '/base_objects/tree_add_item.mustache',
          draw_children: true,
        },
        Objective: {
          draw_children: true,
          add_item_view: path + '/base_objects/tree_add_item.mustache',
        },
        Control: {
          draw_children: true,
          add_item_view: path + '/base_objects/tree_add_item.mustache',
        },
        Issue: {
          draw_children: true,
        },
        AccessGroup: {
          draw_children: true,
        },
        DataAsset: {
          draw_children: true,
        },
        Facility: {
          draw_children: true,
        },
        Market: {
          draw_children: true,
        },
        Metric: {
          draw_children: true,
        },
        OrgGroup: {
          draw_children: true,
        },
        Vendor: {
          draw_children: true,
        },
        Process: {
          draw_children: true,
        },
        Product: {
          draw_children: true,
        },
        ProductGroup: {
          draw_children: true,
        },
        Project: {
          draw_children: true,
        },
        System: {
          draw_children: true,
        },
        Assessment: {
          draw_children: true,
          add_item_view: null,
        },
        Risk: {
          draw_children: true,
        },
        TechnologyEnvironment: {
          draw_children: true,
        },
        Threat: {
          draw_children: true,
        },
      },
    });

    // Disable editing on profile pages, as long as it isn't audits on the dashboard
    if (getPageInstance() instanceof businessModels.Person) {
      let personOptions = extraContentOptions.Person;
      can.each(personOptions, function (options, modelName) {
        if (modelName !== 'Audit' || !/dashboard/.test(window.location)) {
          can.extend(options, {
            allow_creating: false,
            allow_mapping: true,
          });
        }
      });
    }

    can.each(farModels, function (modelName) {
      let widgetConfig = getWidgetConfig(modelName);
      modelName = widgetConfig.name;

      let farModel;
      let descriptor = {};
      let widgetId;

      farModel = businessModels[modelName];
      if (farModel) {
        widgetId = widgetConfig.widgetId;
        descriptor = {
          instance: object,
          far_model: farModel,
        };
      } else {
        widgetId = modelName;
      }

      // Custom overrides
      if (extraDescriptorOptions.all &&
          extraDescriptorOptions.all[modelName]) {
        $.extend(descriptor, extraDescriptorOptions.all[modelName]);
      }

      if (extraDescriptorOptions[object.constructor.shortName] &&
          extraDescriptorOptions[object.constructor.shortName][modelName]) {
        $.extend(descriptor,
          extraDescriptorOptions[object.constructor.shortName][modelName]);
      }

      if (extraContentOptions[object.constructor.shortName] &&
          extraContentOptions[object.constructor.shortName][modelName]) {
        $.extend(true, descriptor, {
          content_controller_options:
          extraContentOptions[object.constructor.shortName][modelName],
        });
      }
      descriptor.widgetType = 'treeview';
      widgetList.add_widget(
        object.constructor.shortName, widgetId, descriptor);
    });
  },
});
