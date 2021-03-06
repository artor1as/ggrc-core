/*
    Copyright (C) 2018 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

(function (can, $) {
  function modelListLoader(controller, params) {
    let model = controller.options.model;
    let page = new $.Deferred();

    model.findPage(params).then(function (results) {
      let collectionName = model.root_collection + '_collection';
      let collection = results[collectionName] || [];

      page.resolve(new can.Observe.List(collection), results.paging);
    });
    return page;
  }

  CMS.Controllers.TreeLoader('GGRC.Controllers.ListView', {
    defaults: {
      is_related: false,
      model: null,
      extra_params: null,
      search_query: '',
      search_params: null,
      parent_instance: null,
      parent_type: null,
      object_display: null,
      parent_display: null,
      header_view: null,
      list_view: null,
      list_objects: null,
      list_loader: null,
      tooltip_view: '/static/mustache/dashboard/object_tooltip.mustache',
    },
  }, {
    init: function () {
      let that = this;
      if (!this.options.extra_params) {
        this.options.extra_params = {};
      }
      if (!this.options.search_params) {
        this.options.search_params = {};
      }
      this.options.state = new can.Observe();

      this.context = new can.Observe({
        // FIXME: Needed?  Default `pager` to avoid binding issues.
        pager: {
          has_next: function () {
            return false;
          },
        },
      });
      this.context.attr('has_next_page', can.compute(function () {
        let pager = that.context.attr('pager');
        return pager && pager.has_next && pager.has_next();
      }));
      this.context.attr('has_prev_page', can.compute(function () {
        let pager = that.context.attr('pager');
        return pager && pager.has_prev && pager.has_prev();
      }));
      this.context.attr(this.options);

      if (this.options.header_view) {
        can.view(this.options.header_view, $.when(this.context))
          .then(function (frag) {
            if (that.element) {
              that.element.prepend(frag);
            }
          });
      }

      if (!this.options.list) {
        this.options.list_loader = modelListLoader;
      }
    },

    prepare: function () {
      let that = this;
      let params = $.extend({}, this.options.extra_params || {});

      if (this._prepare_deferred) {
        return this._prepare_deferred;
      }

      params.__page_only = true;
      this._prepare_deferred = this.options.list_loader(this, params)
        .then(function (results, pager) {
          that.options.pager = pager;
          that.context.attr('pager', pager);
          that.update_count();
          return results;
        });

      return this._prepare_deferred;
    },

    fetch_list: function (params) {
      // Assemble extra search params
      let extraParams = this.options.extra_params || {};
      let searchParams = this.options.search_params;
      let that = this;

      this.element.trigger('loading');

      if (this.options.list) {
        this.options.list.replace([]);
      }

      params = $.extend({}, params, extraParams);

      if (this.options.model.list_view_options &&
        this.options.model.list_view_options.find_params) {
        params = $.extend(params,
          this.options.model.list_view_options.find_params);
      }

      if (this.options.model.shortName === 'Person') {
        params.__sort = 'name,email';
        if (searchParams.search_term) {
          params.__search = searchParams.search_term;
        }
        if (searchParams.role_id) {
          params['user_roles.role_id'] = searchParams.role_id;
        }
        if (searchParams.noRole) {
          params.__no_role = true;
        }
      }

      return this.options.list_loader(this, params)
        .then(function (results, pager) {
          that.options.pager = pager;
          that.context.attr('pager', pager);
          return results;
        });
    },

    draw_list: function (list) {
      let that = this;

      if (list && this.options.fetch_post_process) {
        list = this.options.fetch_post_process(list);
      }

      if (list) {
        if (!this.options.list) {
          this.options.list = new can.Observe.List();
          list.on('add', function (list, item, index) {
            that.enqueue_items(item);
          }).on('remove', function (list, item, index) {
            that.options.list.splice(index, 1);
            that.element.find('ul.tree-open').removeClass('tree-open');
          });
        } else {
          this.options.list.splice();
        }
        this.enqueue_items(list);
        this.on();
      }

      this.context.attr(this.options);
      this.update_count();
    },

    init_view: function () {
      let that = this;
      return can.view(this.options.list_view, this.context, function (frag) {
        that.element.find('.spinner, .tree-structure').hide();
        that.element
          .append(frag)
          .trigger('loaded');
        that.options.state.attr('loading', false);
      });
    },

    update_count: function () {
      if (this.element) {
        if (this.options.pager) {
          this.element.trigger('updateCount', this.options.pager.total);
        }
        this.element.trigger('widget_updated');
      }
    },

    reset_search: function (el, ev) {
      this.options.search_params = {};
      this.options.search_query = '';
      this.element.find('.search-filters')
        .find('input[name=search], select[name=user_role]').val('');
      this.fetch_list().then(this.proxy('draw_list'));
    },

    insert_items: function (items) {
      this.options.list.push(...items);
      return can.Deferred().resolve();
    },

    '{list} change': 'update_count',

    '.view-more-paging click': function (el, ev) {
      let that = this;
      let collectionName = that.options.model.root_collection + '_collection';
      let isNext = el.data('next');
      let canLoad = isNext ?
        that.options.pager.has_next() : that.options.pager.has_prev();
      let load = isNext ? that.options.pager.next : that.options.pager.prev;

      that.options.list.replace([]);
      that.element.find('.spinner').show();
      if (canLoad) {
        load().done(function (data) {
          that.element.find('.spinner').hide();
          if (typeof data === 'undefined') {
            return;
          }
          if (data[collectionName] && data[collectionName].length > 0) {
            that.enqueue_items(data[collectionName]);
          }
          that.options.pager = data.paging;
          that.context.attr('pager', data.paging);
        });
      }
    },

    '.search-filters input[name=search] change': function (el, ev) {
      this.options.search_params.search_term = el.val();
      this.fetch_list().then(this.proxy('draw_list'));
    },

    '.search-filters select[name=user_role] change': function (el, ev) {
      let value = el.val();
      if (value === 'no-role') {
        this.options.search_params.noRole = true;
        this.options.search_params.role_id = undefined;
      } else {
        this.options.search_params.noRole = false;
        this.options.search_params.role_id = value;
      }
      this.fetch_list().then(this.proxy('draw_list'));
    },

    '.search-filters button[type=reset] click': 'reset_search',
    '.btn-add modal:success': 'reset_search',
  });
})(window.can, window.can.$);
