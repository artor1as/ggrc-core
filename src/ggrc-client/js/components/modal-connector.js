/*
 Copyright (C) 2018 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import {
  isSnapshotType,
} from '../plugins/utils/snapshot-utils';
import Mappings from '../models/mappers/mappings';
import * as MapperUtils from '../plugins/utils/mapper-utils';
import * as businessModels from '../models/business-models';
import {
  REFRESH_MAPPING,
  REFRESH_SUB_TREE,
} from '../events/eventTypes';

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
    useSnapshots: false,
    instance: null,
    source_mapping: '@',
    default_mappings: [], // expects array of objects
    mapping: '@',
    list: [],
    needToInstanceRefresh: true,
    // the following are just for the case when we have no object to start with,
    changes: [],
    performMapActions(instance, objects) {
      let pendingMap = Promise.resolve();

      if (objects.length > 0) {
        pendingMap = MapperUtils.mapObjects(instance, objects, {
          useSnapshots: this.attr('useSnapshots'),
        });
      }

      return pendingMap;
    },
    performUnmapActions(instance, objects) {
      let pendingUnmap = Promise.resolve();

      if (objects.length > 0) {
        pendingUnmap = MapperUtils.unmapObjects(instance, objects);
      }

      return pendingUnmap;
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
    afterDeferredUpdate(objects) {
      const instance = this.attr('instance');
      const objectTypes = _.uniq(objects
        .map((object) => object.constructor.shortName)
      );

      objectTypes.forEach((objectType) => {
        instance.dispatch({
          ...REFRESH_MAPPING,
          destinationType: objectType,
        });
      });
      instance.dispatch(REFRESH_SUB_TREE);
    },
    handlePendingOperations(pendingJoins) {
      const instance = this.attr('instance');
      const getObject = (pj) => pj.what;
      const objectsForMap = pendingJoins.filter((pj) => pj.how === 'add')
        .map(getObject);
      const objectsForUnmap = pendingJoins.filter((pj) => pj.how === 'remove')
        .map(getObject);

      return Promise.all([
        this.performMapActions(instance, objectsForMap),
        this.performUnmapActions(instance, objectsForUnmap),
      ]);
    },
    async deferredUpdate() {
      const instance = this.attr('instance');

      this.preparePendingJoins();

      // We need to remove all _pending_joins from the instance (via splice())
      // in order to resolveDeferredBindings util after instance.save
      // via modal functionality doesn't handle it second time.
      const pendingJoins = instance._pending_joins.splice(0);
      await this.handlePendingOperations(pendingJoins);
      const objects = pendingJoins.map((pj) => pj.what);
      this.afterDeferredUpdate(objects);
    },
    addMappings(objects) {
      can.each(objects, (obj) => {
        const changes = this.attr('changes');
        const indexOfRemoveChange = this.findObjectInChanges(obj, 'remove');

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
    removeMappings(obj) {
      let len = this.list.length;
      const changes = this.changes;
      const indexOfAddChange = this.findObjectInChanges(obj, 'add');

      if (indexOfAddChange !== -1) {
        // remove "add" change
        changes.splice(indexOfAddChange, 1);
      } else {
        // add "remove" change
        changes.push({what: obj, how: 'remove'});
      }

      for (; len >= 0; len--) {
        if (this.list[len] === obj) {
          this.list.splice(len, 1);
        }
      }
    },
    addListItem(item) {
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

      this.list.push(item);
    },
    setListItems(list) {
      let currentList = this.attr('list');
      this.attr('list', currentList.concat(can.map(list,
        function (binding) {
          return binding.instance || binding;
        })));
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
          that.viewModel.addListItem(objectToAdd);
        }
      });

      if (!vm.source_mapping) {
        vm.attr('source_mapping', vm.mapping);
      }

      if (!vm.attr('customRelatedLoader')) {
        Mappings.get_binding(vm.source_mapping, instance)
          .refresh_instances()
          .then(function (list) {
            this.viewModel.setListItems(list);
          }.bind(this));
      }

      this.on();
    },
    '{instance} updated'() {
      this.viewModel.deferredUpdate();
    },
    '{instance} created'() {
      this.viewModel.deferredUpdate();
    },
    '[data-toggle=unmap] click'(el, ev) {
      const unmapObject = el.find('.result').data('result');
      ev.stopPropagation();
      this.viewModel.removeMappings(unmapObject);
    },
    'a[data-object-source] modal:success'(el, ev, object) {
      ev.stopPropagation();
      this.viewModel.addMappings([object]);
    },
    'defer:add'(el, ev, {arr: objects}) {
      ev.stopPropagation();
      this.viewModel.addMappings(objects);
    },
  },
});
