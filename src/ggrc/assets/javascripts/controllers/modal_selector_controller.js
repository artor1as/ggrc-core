/*
 * Copyright (C) 2013 Google Inc., authors, and contributors <see AUTHORS file>
 * Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 * Created By: dan@reciprocitylabs.com
 * Maintained By: dan@reciprocitylabs.com
 */

(function(can, $) {

  /* Modal Selector
   *
   * parameters:
   *   Templates:
   *     base_modal_view:
   *     option_column_view:
   *     active_column_view:
   *     option_object_view:
   *     active_object_view:
   *     option_detail_view:
   *
   *   Models and Queries:
   *     option_model: The model being "selected" (the "many")
   *     option_query:
   *       Any additional parameters needed to restrict valid options
   *     active_query:
   *       Any additional parameters needed to restrict active options
   *     join_model: The model representing the join table
   *     join_query:
   *       Any additional parameters needed to restrict the join results
   *
   *   Customizable text components:
   *     modal_title:
   *     option_list_title:
   *     active_list_title:
   *     new_object_title:
   */

  can.Control("GGRC.Controllers.ModalSelector", {
    _templates: [
      "base_modal_view",
      "option_column_view",
      "active_column_view",
      "option_object_view",
      "active_object_view",
      "option_detail_view"
    ],

    defaults: {
      base_modal_view: GGRC.mustache_path + "/selectors/base_modal.mustache",
      option_column_view: GGRC.mustache_path + "/selectors/option_column.mustache",
      active_column_view: GGRC.mustache_path + "/selectors/active_column.mustache",
      option_object_view: null, //GGRC.mustache_path + "/selectors/option_object.mustache",
      active_object_view: null, //GGRC.mustache_path + "/selectors/active_object.mustache",
      option_detail_view: GGRC.mustache_path + "/selectors/option_detail.mustache",

      option_model: null,
      option_query: {},
      active_query: {},
      join_model: null,
      join_query: {},
      join_object: null,
      join_object_id: null,
      join_object_type: null,

      modal_title: null,
      option_list_title: null,
      active_list_title: null,
      new_object_title: null,
    },

    launch: function($trigger, options) {
      // Extract parameters from data attributes

      var href = $trigger.attr('data-href') || $trigger.attr('href')
        , modal_id = 'ajax-modal-' + href.replace(/[\/\?=\&#%]/g, '-').replace(/^-/, '')
        , $target = $('<div id="' + modal_id + '" class="modal modal-selector hide"></div>')
        ;

      $target.modal_form({}, $trigger);
      this.newInstance($target[0], $.extend({ $trigger: $trigger}, options));
      return $target;
    }
  }, {
    init: function() {
      var self = this
        , _data_changed = false
        ;

      this.option_list = new can.Observe.List();
      this.join_list = new can.Observe.List();
      this.active_list = new can.Observe.List();

      this.join_list.bind("change", function() {
        self.active_list.replace(
          can.map(self.join_list, function(join) {
            return new can.Observe({
              option: CMS.Models.get_instance(
                self.options.option_model.shortName || CMS.Models.get_link_type(join, self.options.option_attr),
                join[self.options.option_id_field] || join[self.options.option_attr].id)
            , join: join
            });
          }))
      });

      this.join_list.bind("change", function() {
        // FIXME: This is to update the Document and Person lists when the
        //   selected items change -- that list should be Can-ified.
        var list_target = self.options.$trigger.data('list-target');
        if (list_target)
          $(list_target)
          .tmpl_setitems(self.join_list)
          .closest(":has(.grc-badge)")
          .find(".grc-badge")
          .text("(" + self.join_list.length + ")");
      });

      $.when(
        this.post_init(),
        this.fetch_data()
      ).then(
        this.proxy('post_draw')
      );
    },

    fetch_data: function() {
      var self = this
        , join_query = can.extend({}, this.options.join_query)
        ;

      join_query[this.options.join_id_field] = this.get_join_object_id();
      if (this.options.join_type_field) {
        join_query[this.options.join_type_field] = this.get_join_object_type();
      }
      $.extend(join_query, this.options.extra_join_fields);

      return $.when(
        this.options.option_model.findAll(
          $.extend({}, this.option_query),
          function(options) {
            self.option_list.replace(options)
          }),
        this.options.join_model.findAll(
          $.extend({}, join_query),
          function(joins) {
            //can.each(joins, function(join) {
            //  join.attr('_removed', false);
            //});
            self.join_list.replace(joins);
          })
        );
    },

    post_init: function() {
      var self = this
        , deferred = $.Deferred()
        ;

      this.context = new can.Observe($.extend({
        options: this.option_list,
        joins: this.join_list,
        actives: this.active_list,
        selected_option: null,
      }, this.options));

      can.view(
        this.options.base_modal_view,
        this.context,
        function(frag) {
          $(self.element).html(frag);
          deferred.resolve();
          //self.post_draw();
        });

      // Start listening for events
      this.on();

      return deferred;
    },

    post_draw: function() {
      var self = this
        , $option_list = $(this.element).find('.selector-list ul')
        ;

      this.join_list.forEach(function(join, index, list) {
        $option_list
          .find('li[data-id=' + join[self.options.option_attr].id + '] input[type=checkbox]')
          .prop('checked', true);
      });
    },

    // EVENTS

    " hide": function(el, ev) {
      // FIXME: This should only happen if there has been a change.
      //   - (actually, the "Related Widget" should just be Can-ified instead)
      var list_target = this.options.$trigger.data('list-target');
      if (list_target === "refresh" && this._data_changed)
        setTimeout(can.proxy(window.location.reload, window.location), 10);
    },

    ".option_column li click": function(el, ev) {
      var option = el.data('option')
        ;

      el.closest('.modal-content').find('li').each(function() {
        $(this).removeClass('selected');
      });
      el.addClass('selected');
      this.context.attr('selected_option', option);
    },

    ".option_column li input[type='checkbox'] change": function(el, ev) {
      var self = this
        , option = el.closest('li').data('option')
        , join = this.find_join(option.id)
        ;

      // FIXME: This is to trigger a page refresh only when data has changed
      //   - currently only used for the Related widget (see the " hide" event)
      this._data_changed = true;

      if (el.is(':checked')) {
        // First, check if join instance already exists
        if (join) {
          // Ensure '_removed' attribute is false
          //join.attr('_removed', false);
        } else {
          // Otherwise, create it
          join = this.get_new_join(option.id, option.constructor.getRootModelName());
          join.save().then(function() {
            //join.refresh().then(function() {
              self.join_list.push(join);
              self.element.trigger("relationshipcreated", join);
            //});
          });
        }
      } else {
        // Check if instance is still selected
        if (join) {
          // Ensure '_removed' attribute is false
          if (join.isNew()) {
            // It was created, then removed, so remove from list
            join_index = this.join_list.indexOf(join);
            if (join_index >= 0) {
              this.join_list.splice(join_index, 1);
            }
          } else {
            // FIXME: The data should be updated in bulk, and only when "Save"
            //   is clicked.  Right now, it updates continuously.
            //join.attr('_removed', true);
            join.refresh().done(function() {
              join.destroy().then(function() {
                join_index = self.join_list.indexOf(join);
                if (join_index >= 0) {
                  self.join_list.splice(join_index, 1);
                }
                self.element.trigger("relationshipdestroyed", join);
              });
            });
          }
        }
      }
    },

    // HELPERS

    find_join: function(option_id) {
      var self = this
        ;

      return can.reduce(
        this.join_list,
        function(result, join) {
          if (result)
            return result;
          if (self.match_join(option_id, join))
            return join;
        },
        null);
    },

    match_join: function(option_id, join) {
      return join[this.options.option_id_field] == option_id ||
        (join[this.options.option_attr] 
         && join[this.options.option_attr].id == option_id)
    },

    get_new_join: function(option_id, option_type) {
      var join_params = {};
      join_params[this.options.option_attr] = {}
      join_params[this.options.option_attr].id = option_id;
      //join_params[this.options.option_id_field] = option_id;
      if (this.options.option_type_field) {
        join_params[this.options.option_attr].type = option_type;
        //join_params[this.options.option_type_field] = option_type;
      }
      join_params[this.options.join_attr] = {}
      join_params[this.options.join_attr].id = this.get_join_object_id();
      //join_params[this.options.join_id_field] = this.get_join_object_id();
      if (this.options.join_type_field) {
        join_params[this.options.join_attr].type = this.get_join_object_type();
        //join_params[this.options.join_type_field] = this.get_join_object_type();
      }
      // FIXME: context_id must get a real value
      $.extend(join_params, this.options.extra_join_fields, { context: { id: null } });
      return new (this.options.join_model)(join_params);
    },

    get_join_object_id: function() {
      return this.options.join_object_id || this.options.join_object.id;
    },

    get_join_object_type: function() {
      return this.options.join_object_type || this.options.join_object.constructor.getRootModelName();
    },

  });

  function get_page_object() {
    return GGRC.make_model_instance(GGRC.page_object);
  }

  function get_option_set(name, data) {
    // Construct options for Person and Reference selectors
    var OPTION_SETS = {
      object_documents: {
        option_column_view: GGRC.mustache_path + "/documents/option_column.mustache",
        active_column_view: GGRC.mustache_path + "/documents/active_column.mustache",
        option_detail_view: GGRC.mustache_path + "/documents/option_detail.mustache",

        new_object_title: "Document",
        modal_title: "Select References",

        related_model_singular: "Document",
        related_table_plural: "documents",
        related_title_singular: "Document",
        related_title_plural: "Documents",

        option_model: CMS.Models.Document,

        join_model: CMS.Models.ObjectDocument,
        option_attr: 'document',
        join_attr: 'documentable',
        option_id_field: 'document_id',
        option_type_field: null,
        join_id_field: 'documentable_id',
        join_type_field: 'documentable_type',

        join_object: get_page_object(),
      },

      object_people: {
        option_column_view: GGRC.mustache_path + "/people/option_column.mustache",
        active_column_view: GGRC.mustache_path + "/people/active_column.mustache",
        option_detail_view: GGRC.mustache_path + "/people/option_detail.mustache",

        new_object_title: "Person",
        modal_title: "Select People",

        related_model_singular: "Person",
        related_table_plural: "people",
        related_title_singular: "Person",
        related_title_plural: "People",

        option_model: CMS.Models.Person,

        join_model: CMS.Models.ObjectPerson,
        option_attr: 'person',
        join_attr: 'personable',
        option_id_field: 'person_id',
        option_type_field: null,
        join_id_field: 'personable_id',
        join_type_field: 'personable_type',

        join_object: get_page_object(),
      },

      system_systems: {
        option_column_view: GGRC.mustache_path + "/selectors/option_column.mustache",
        active_column_view: GGRC.mustache_path + "/selectors/active_column.mustache",
        option_detail_view: GGRC.mustache_path + "/selectors/option_detail.mustache",

        new_object_title: "System",
        modal_title: "Select Systems",

        related_model_singular: "System",
        related_table_plural: "systems",
        related_title_singular: "System",
        related_title_plural: "Systems",

        option_model: CMS.Models.System,

        join_model: CMS.Models.SystemSystem,
        option_attr: 'child',
        join_attr: 'parent',
        option_id_field: 'child_id',
        option_type_field: null,
        join_id_field: 'parent_id',
        join_type_field: null,

        join_object: CMS.Models.System.findInCacheById(data.join_object_id)
      },

      system_controls: {
        option_column_view: GGRC.mustache_path + "/selectors/option_column.mustache",
        active_column_view: GGRC.mustache_path + "/selectors/active_column.mustache",
        option_detail_view: GGRC.mustache_path + "/selectors/option_detail.mustache",

        new_object_title: "Control",
        modal_title: "Select Controls",

        related_model_singular: "Control",
        related_table_plural: "controls",
        related_title_singular: "Control",
        related_title_plural: "Controls",

        option_model: CMS.Models.Control,

        join_model: CMS.Models.SystemControl,
        option_attr: 'control',
        join_attr: 'system',
        option_id_field: 'control_id',
        option_type_field: null,
        join_id_field: 'system_id',
        join_type_field: null,

        join_object: CMS.Models.System.findInCacheById(data.join_object_id)
      }
      , program_directives : {
        option_column_view: GGRC.mustache_path + "/selectors/option_column.mustache",
        active_column_view: GGRC.mustache_path + "/selectors/active_column.mustache",
        option_detail_view: GGRC.mustache_path + "/selectors/option_detail.mustache",

        new_object_title: data.related_title_singular,
        modal_title: "Select " + data.related_title_plural,

        related_model_singular: "Directive",
        related_table_plural: "directives",
        related_title_singular: "System",
        related_title_plural: "Systems",

        option_model: CMS.Models[data.child_meta_type],
        join_model: CMS.Models.ProgramDirective,

        option_attr: 'directive',
        join_attr: 'program',
        option_id_field: 'directive_id',
        option_type_field: 'directive_type',
        join_id_field: 'program_id',
        join_type_field: null,

        join_object: CMS.Models.Program.findInCacheById(data.join_object_id)
      }

      , section_objectives : {
        option_column_view: GGRC.mustache_path + "/selectors/option_column.mustache",
        active_column_view: GGRC.mustache_path + "/selectors/active_column.mustache",
        option_detail_view: GGRC.mustache_path + "/selectors/option_detail.mustache",

        new_object_title: "Objective",
        modal_title: "Select Objectives",

        related_model_singular: "Objective",
        related_table_plural: "objectives",
        related_title_singular: "Objective",
        related_title_plural: "Objectives",

        object_model: CMS.Models.Section,
        option_model: CMS.Models.Objective,
        join_model: CMS.Models.SectionObjective,

        option_attr: 'objective',
        join_attr: 'section',
        option_id_field: 'objective_id',
        //option_type_field: 'objective_type',
        join_id_field: 'section_id',
        join_type_field: null,

        join_object: CMS.Models.Section.findInCacheById(data.join_object_id)
      }

      , risk_controls : {
        option_column_view: GGRC.mustache_path + "/selectors/option_column.mustache",
        active_column_view: GGRC.mustache_path + "/selectors/active_column.mustache",
        option_detail_view: GGRC.mustache_path + "/selectors/option_detail.mustache",

        new_object_title: data.related_title_singular,
        modal_title: "Select " + data.related_title_plural,

        related_model_singular: "Risk",
        related_table_plural: "risks",
        related_title_singular: "Risk",
        related_title_plural: "Risks",

        option_model: CMS.Models.Control,
        join_model: CMS.Models.RiskControl,

        option_attr: 'control',
        join_attr: 'risk',
        option_id_field: 'control_id',
        option_type_field: 'control_type',
        join_id_field: 'risk_id',
        join_type_field: null,

        join_object: CMS.Models.Program.findInCacheById(data.join_object_id)
      }
    };
    return can.extend(OPTION_SETS[name], {
      join_query : can.deparam(data.join_query)
    });
  }

  function get_relationship_option_set(data) {
    // Construct options for selectors in the Related widget
    var options = {};
    options.new_object_title = data.related_title_singular;
    options.modal_title = "Select " + data.related_title_plural;

    options.related_model_singular = data.related_model_singular;
    options.related_table_plural = data.related_table_plural;
    options.related_title_singular = data.related_title_singular;
    options.related_title_plural = data.related_title_plural;

    data.related_table_plural = 'selectors';

    option_column_view =
      GGRC.mustache_path + "/" + data.related_table_plural + "/option_column.mustache";
    active_column_view =
      GGRC.mustache_path + "/" + data.related_table_plural + "/active_column.mustache";
    option_detail_view =
      GGRC.mustache_path + "/" + data.related_table_plural + "/option_detail.mustache";

    options.option_model = CMS.Models[data.related_model];
    options.join_model = CMS.Models.Relationship;

    if (data.related_side === "destination") {
      data.object_side = "source";
    } else if (data.related_side === "source") {
      data.object_side = "destination";
    }

    options.option_attr = data.object_side;
    options.join_attr = data.related_side;
    options.option_id_field = data.object_side + "_id";
    options.option_type_field = data.object_side + "_type";
    options.join_id_field = data.related_side + "_id";
    options.join_type_field = data.related_side + "_type";

    if (data.join_object_id && data.join_object_type) {
      options.join_object_id = data.join_object_id;
      options.join_object_type = data.join_object_type;
    } else {
      options.join_object = get_page_object();
      options.join_object_id = options.join_object.id;
      options.join_object_type = options.join_object_type;
    }

    options.extra_join_fields = {
      relationship_type_id: data.relationship_type
    };

    options.extra_join_fields[options.option_type_field] = options.option_model.shortName;


    return options;
  }

  $(function() {
    $('body').on('click', '[data-toggle="modal-relationship-selector"]', function(e) {
      var $this = $(this)
        ;

      e.preventDefault();

      // Trigger the controller
      GGRC.Controllers.ModalSelector.launch(
        $this, get_relationship_option_set({
            related_model_singular: $this.data('related-model-singular')
          , related_title_singular: $this.data('related-title-singular')
          , related_title_plural: $this.data('related-title-plural')
          , related_table_plural: $this.data('related-table-plural')
          , related_side: $this.data('related-side')
          , related_model: $this.data('related-model')
          , join_object_id: $this.data('join-object-id')
          , join_object_type: $this.data('join-object-type')
          , object_side: $this.data('object-side')
          , relationship_type: $this.data('relationship-type')
          , join_query: $this.data('join-query')
        })).on("relationshipcreated relationshipdestroyed", function(ev, data) {
          $this.trigger("modal:" + ev.type, data);
        });
    });
  });

  $(function() {
    $('body').on('click', '[data-toggle="modal-selector"]', function(e) {
      var $this = $(this)
        , options = $this.data('modal-selector-options')
        , data_set = can.extend({}, $this.data())
        ;

      can.each($this.data(), function(v, k) {
        data_set[k.replace(/[A-Z]/g, function(s) { return "_" + s.toLowerCase(); })] = v; //this is just a mapping of keys to underscored keys
        if(!/[A-Z]/.test(k)) //if we haven't changed the key at all, don't delete the original
          delete data_set[k];
      });

      if (typeof(options) === "string")
        options = get_option_set(
          options
          , data_set
        );

      e.preventDefault();

      // Trigger the controller
      GGRC.Controllers.ModalSelector.launch($this, options)
      .on("relationshipcreated relationshipdestroyed", function(ev, data) {
        $this.trigger("modal:" + ev.type, data);
      });
    });
  });


  can.Control("GGRC.Controllers.MultitypeModalSelector", {
      defaults: {
          option_type_menu: null
        , option_descriptors: null
        , base_modal_view: "/static/mustache/selectors/multitype_base_modal.mustache"
        , object_detail_view: "/static/mustache/selectors/multitype_object_detail.mustache"
        , option_type: null
        , option_model: null
        , object_model: null
        , join_model: null
      }
    , launch: function($trigger, options) {
        // Extract parameters from data attributes

        var href = $trigger.attr('data-href') || $trigger.attr('href')
          , modal_id = 'ajax-modal-' + href.replace(/[\/\?=\&#%]/g, '-').replace(/^-/, '')
          , $target = $('<div id="' + modal_id + '" class="modal modal-selector hide"></div>')
          ;

        $target.modal_form({}, $trigger);
        this.newInstance($target[0], $.extend({ $trigger: $trigger}, options));
        return $target;
      }
  }, {
      init: function() {
        this.object_list = new can.Observe.List();
        this.option_list = new can.Observe.List();
        this.join_list = new can.Observe.List();
        this.active_list = new can.Observe.List();

        this.init_context();
        this.set_option_descriptor(this.options.default_option_descriptor);
        this.init_bindings();
        this.init_view();
        this.init_data()
      }

    , init_bindings: function() {
      }

    , init_view: function() {
        var self = this
          , deferred = $.Deferred()
          ;

        can.view(
          this.options.base_modal_view,
          this.context,
          function(frag) {
            $(self.element).html(frag);
            deferred.resolve();
          });

        // Start listening for events
        this.on();

        return deferred;
      }

    , init_data: function() {
        return $.when(
          this.refresh_option_list()
        );
      }

    , init_context: function() {
        if (!this.context) {
          this.context = new can.Observe($.extend({
            objects: this.object_list,
            options: this.option_list,
            joins: this.join_list,
            actives: this.active_list,
            selected_object: null,
            selected_option_type: null,
            selected_option: null,
          }, this.options));
        }
        return this.context;
      }

    , refresh_option_list: function() {
        var self = this
          ;

        return this.options.option_model.findAll(
          $.extend({}, this.option_query),
          function(options) {
            self.option_list.replace(options)
          });
      }

    , set_option_descriptor: function(option_type) {
        var descriptor = this.options.option_descriptors[option_type]
          ;

        can.Model.startBatch();

        this.context.attr('selected_option_type', option_type);
        this.context.attr('option_column_view', descriptor.column_view);
        this.context.attr('option_detail_view', descriptor.detail_view);
        this.context.attr('option_descriptor', descriptor);
        this.context.attr('selected_option', null);
        this.options.option_model = descriptor.model;

        this.refresh_option_list().always(function() {
          can.Model.stopBatch();
        });
      }

    , on_select_option_type: function(el, ev) {
        this.set_option_descriptor($(el).val());
      }

    , "select.option-type-selector change": "on_select_option_type"

    , "{selected_object_type} change": "refresh_option_list"

    , ".option_column li click": "on_select_option"

    , on_select_option: function(el) {
        el.closest('.option_column').find('li').removeClass('selected');
        el.addClass('selected');
        this.context.attr('selected_option', el.data('option'));
      }

    , ".map-button click": "on_map"

    , on_map: function(el, ev) {
        var that = this
          ;

        this.create_join()
          .done(function() {
            $(that.element).modal_form('hide');
          })
          .fail(function() {
            //alert("Fail");
          });
      }

    , create_join: function() {
        if (this.context.selected_option) {
          join = this.context.option_descriptor.get_new_join(
              this.context.selected_object, this.context.selected_option, null);
          //join = this.get_new_join(this.context.selected_option);
          return join.save();
        } else {
          return (new $.Deferred()).reject();
        }
      }
  });

  ModalOptionDescriptor = can.Construct({
      model : "DataAsset"
    , model_display : "Data Assets"
    , join_model : "ObjectObjective"
    , join_option_attr : "objectiveable"
    , column_view : GGRC.mustache_path + "/selectors/option_column.mustache"
    , detail_view : GGRC.mustache_path + "/selectors/multitype_option_detail.mustache"

    , from_join_model: function(join_model, join_option_attr, model, options) {
        join_model = this.get_model(join_model);
        model = this.get_model(model);

        // The 'object_attr' is the join key that is *not* the 'option_attr'
        join_object_attr = can.map(join_model.join_keys, function(v, k) {
          if (k !== join_option_attr)
            return k;
        })[0];

        // Detect polymorphic join attrs
        if (this.model === can.Model.Cacheable)
          console.error("Polymorphic joins must have explicit target models");

        return this({
            join_model: join_model
          , join_model_name: join_model.shortName
          , join_option_attr: join_option_attr
          , join_object_attr: join_object_attr
          , model: model
          , model_display: model.title_plural
        }, {});
      }

    , get_model: function(model) {
        if (model.shortName)
          return model;
        else if (CMS.Models[model])
          return CMS.Models[model];
        else
          console.error("Unknown model: ", model);
      }

    , get_new_join: function(object, option, context_id) {
        var join_params = {};

        join_params[this.join_option_attr] = {};
        join_params[this.join_option_attr].id = option.id;
        join_params[this.join_option_attr].type = option.constructor.getRootModelName();
        join_params[this.join_object_attr] = {};
        join_params[this.join_object_attr].id = object.id;
        join_params[this.join_object_attr].type = object.constructor.getRootModelName();
        join_params.context = { id: context_id };
        return new (this.join_model)(join_params);
      }
  }, {});

  function make_join_model_modal_option_descriptors(join_model, join_option_attr, models) {
    var descriptors = {};
    if (!(models instanceof Array))
      models = [models];

    can.each(models, function(model) {
      var descriptor = ModalOptionDescriptor.from_join_model(
        join_model, join_option_attr, model);
      descriptors[descriptor.model.shortName] = descriptor;
    });
    return descriptors;
  }

  var join_descriptors = {
      section_objects: {
      }

    , objective_objects: {
        model: "ObjectObjective"
      , object_model: "Objective"
      , join_model: "ObjectObjective"

      , default_option_descriptor: "DataAsset"
      , option_type_menu: [
            { category: "Assets/Business"
            , items: [
                { model_name: "DataAsset", model_display: "Data Assets" }
              , { model_name: "Facility", model_display: "Facilities" }
              , { model_name: "Market", model_display: "Markets" }
              , { model_name: "OrgGroup", model_display: "Org Groups" }
              , { model_name: "Process", model_display: "Processes" }
              , { model_name: "Product", model_display: "Products" }
              , { model_name: "Project", model_display: "Projects" }
              , { model_name: "System", model_display: "Systems" }
              ]
            }
          , { category: "Governance"
            , items: [
                { model_name: "Section", model_display: "Sections" }
              , { model_name: "Control", model_display: "Controls" }
              ]
            }
          ]
      , option_descriptors: $.extend(
            make_join_model_modal_option_descriptors(
              "ObjectObjective", "objectiveable",
              [
                "DataAsset", "Facility", "Market", "OrgGroup",
                "Process", "Product", "Project", "System"
              ])
          , make_join_model_modal_option_descriptors(
              "SectionObjective", "section", ["Section"])
          , make_join_model_modal_option_descriptors(
              "ObjectiveControl", "control", ["Control"])
          )
      }
    }

  $(function() {
    $('body').on('click', '[data-toggle="multitype-modal-selector"]', function(e) {
      var $this = $(this)
        , options = $this.data('modal-selector-options')
        , data_set = can.extend({}, $this.data())
        ;

      can.each($this.data(), function(v, k) {
        data_set[k.replace(/[A-Z]/g, function(s) { return "_" + s.toLowerCase(); })] = v; //this is just a mapping of keys to underscored keys
        if(!/[A-Z]/.test(k)) //if we haven't changed the key at all, don't delete the original
          delete data_set[k];
      });

      /*if (typeof(options) === "string")
        options = get_option_set(
          options
          , data_set
        );*/

      options = $.extend({}, join_descriptors.objective_objects);
      options.selected_object = CMS.Models.get_instance(
          data_set.join_object_type, data_set.join_object_id);

      e.preventDefault();

      // Trigger the controller
      GGRC.Controllers.MultitypeModalSelector.launch($this, options)
      .on("relationshipcreated relationshipdestroyed", function(ev, data) {
        $this.trigger("modal:" + ev.type, data);
      });
    });
  });

})(window.can, window.can.$);
