/*
 Copyright (C) 2018 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import {
  isSnapshotType,
} from '../plugins/utils/snapshot-utils';
import {
  handlePendingJoins,
} from '../models/pending-joins';
import Mappings from '../models/mappers/mappings';
import * as businessModels from '../models/business-models';

/*
 Below this line we're defining a can.Component, which is in this file
 because it works in tandem with the modals form controller.

 The purpose of this component is to allow for pending adds/removes of connected
 objects while the modal is visible.  On save, the actual pending actions will
 be resolved and we won't worry about the transient state we use anymore.
 */
export default can.Component.extend({
  tag: 'ggrc-modal-connector',
  // <content> in a component template will be replaced with whatever is contained
  //  within the component tag.  Since the views for the original uses of these components
  //  were already created with content, we just used <content> instead of making
  //  new view template files.
  template: '<isolate-form><content/></isolate-form>',
  viewModel: {
    define: {
      customRelatedLoader: {
        type: Boolean,
        value: false,
      },
    },
    instance: null,
    source_mapping: '@',
    default_mappings: [], // expects array of objects
    mapping: '@',
    list: [],
    needToInstanceRefresh: true,
    // the following are just for the case when we have no object to start with,
    changes: [],
    makeDelayedResolving() {
      const instance = this.attr('instance');
      const dfd = handlePendingJoins(instance);
      instance.delay_resolving_save_until(dfd);
    },
    preparePendingJoins() {
      can.each(this.attr('changes'), (item) => {
        let mapping = this.mapping ||
            Mappings.get_canonical_mapping_name(
              this.instance.constructor.shortName,
              item.what.constructor.shortName);
        if (item.how === 'add') {
          this.instance
            .mark_for_addition(mapping, item.what, item.extra);
        } else {
          this.instance.mark_for_deletion(mapping, item.what);
        }
      });
    },
    findObjectInChanges(object, changeType) {
      return _.findIndex(this.attr('changes'), (change) => {
        const {what} = change;
        return (
          what.id === object.id &&
          what.type === object.type &&
          change.how === changeType
        );
      });
    },
  },
  events: {
    init: function () {
      let that = this;
      let vm = this.viewModel;
      vm.attr('controller', this);
      if (vm.instance.reify) {
        vm.attr('instance', vm.instance.reify());
      }

      const instance = vm.attr('instance');
      vm.default_mappings.forEach(function (defaultMapping) {
        let model;
        let objectToAdd;
        if (defaultMapping.id && defaultMapping.type) {
          model = businessModels[defaultMapping.type];
          objectToAdd = model.findInCacheById(defaultMapping.id);
          instance
            .mark_for_addition('related_objects_as_source', objectToAdd, {});
          that.addListItem(objectToAdd);
        }
      });

      if (!vm.source_mapping) {
        vm.attr('source_mapping', vm.mapping);
      }

      if (!vm.attr('customRelatedLoader')) {
        Mappings.get_binding(vm.source_mapping, instance)
          .refresh_instances()
          .then(function (list) {
            this.setListItems(list);
          }.bind(this));
      }

      this.on();
    },
    setListItems: function (list) {
      let currentList = this.viewModel.attr('list');
      this.viewModel.attr('list', currentList.concat(can.map(list,
        function (binding) {
          return binding.instance || binding;
        })));
    },
    deferredUpdate: function () {
      const viewModel = this.viewModel;
      let changes = viewModel.changes;
      let instance = viewModel.instance;

      if (!changes.length) {
        const hasPendingJoins = _.get(instance, '_pending_joins.length') > 0;
        if (hasPendingJoins) {
          viewModel.makeDelayedResolving();
        }
        return;
      }
      // Add pending operations
      viewModel.preparePendingJoins();

      viewModel.makeDelayedResolving();
    },
    '{instance} updated'() {
      this.deferredUpdate();
    },
    '{instance} created'() {
      this.deferredUpdate();
    },
    '[data-toggle=unmap] click': function (el, ev) {
      ev.stopPropagation();

      can.map(el.find('.result'), function (resultEl) {
        let obj = $(resultEl).data('result');
        let len = this.viewModel.list.length;
        const changes = this.viewModel.changes;
        const indexOfAddChange = this.viewModel.findObjectInChanges(obj, 'add');

        if (indexOfAddChange !== -1) {
          // remove "add" change
          changes.splice(indexOfAddChange, 1);
        } else {
          // add "remove" change
          changes.push({what: obj, how: 'remove'});
        }

        for (; len >= 0; len--) {
          if (this.viewModel.list[len] === obj) {
            this.viewModel.list.splice(len, 1);
          }
        }
      }.bind(this));
    },
    'a[data-object-source] modal:success': 'addMapings',
    'defer:add': 'addMapings',
    addMapings(el, ev, data) {
      ev.stopPropagation();

      can.each(data.arr || [data], (obj) => {
        const changes = this.viewModel.attr('changes');
        const indexOfRemoveChange = this.viewModel.findObjectInChanges(obj,
          'remove');

        if (indexOfRemoveChange !== -1) {
          // remove "remove" change
          changes.splice(indexOfRemoveChange, 1);
        } else {
          // add "add" change
          changes.push({what: obj, how: 'add'});
        }

        this.addListItem(obj);
      });
    },
    addListItem: function (item) {
      let snapshotObject;

      if (isSnapshotType(item) &&
        item.snapshotObject) {
        snapshotObject = item.snapshotObject;
        item.attr('title', snapshotObject.title);
        item.attr('description', snapshotObject.description);
        item.attr('class', snapshotObject.class);
        item.attr('snapshot_object_class', 'snapshot-object');
        item.attr('viewLink', snapshotObject.originalLink);
      } else if (!isSnapshotType(item) && item.reify) {
        // add full item object from cache
        // if it isn't snapshot
        item = item.reify();
      }

      this.viewModel.list.push(item);
    },
  },
});
