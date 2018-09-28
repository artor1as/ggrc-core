/*
  Copyright (C) 2018 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import * as SnapshotUtils from '../../../plugins/utils/snapshot-utils';
import RefreshQueue from '../../../models/refresh_queue';
import * as CurrentPageUtils from '../../../plugins/utils/current-page-utils';
import Component from '../object-mapper';
import Program from '../../../models/business-models/program';
import * as modelsUtils from '../../../plugins/utils/models-utils';

describe('object-mapper component', function () {
  let events;
  let viewModel;
  let handler;
  let helpers;

  beforeAll(function () {
    events = Component.prototype.events;
    helpers = Component.prototype.helpers;
  });

  describe('viewModel() method', function () {
    let parentViewModel;
    beforeEach(function () {
      parentViewModel = new can.Map({
        general: {
          useSnapshots: false,
        },
        special: [],
      });
    });

    it(`initializes join_object_id with "join-object-id"
    if isNew flag is not passed`,
    function () {
      parentViewModel.attr('general.join-object-id', 'testId');
      let result = Component.prototype.viewModel({}, parentViewModel)();
      expect(result.join_object_id).toBe('testId');
    });

    it(`initializes join_object_id with page instance id if
    "join-object-id" and "isNew" are not passed`,
    function () {
      spyOn(CurrentPageUtils, 'getPageInstance')
        .and.returnValue({id: 'testId'});
      let result = Component.prototype.viewModel({}, parentViewModel)();
      expect(result.join_object_id).toBe('testId');
    });

    it('initializes join_object_id with null if isNew flag is passed',
      function () {
        parentViewModel.attr('general.isNew', true);
        let result = Component.prototype.viewModel({}, parentViewModel)();
        expect(result.join_object_id).toBe(null);
      });

    it('returns object with function "isLoadingOrSaving"', function () {
      let result = Component.prototype.viewModel({}, parentViewModel)();
      expect(result.isLoadingOrSaving).toEqual(jasmine.any(Function));
    });

    describe('initializes useSnapshots flag', function () {
      it('with true if set with help a general config', function () {
        let result;
        parentViewModel.general.useSnapshots = true;
        result = Component.prototype.viewModel({}, parentViewModel)();
        expect(result.attr('useSnapshots')).toEqual(true);
      });

      it('do not use Snapshots if not an in-scope model', function () {
        let result;
        spyOn(SnapshotUtils, 'isInScopeModel')
          .and.returnValue(false);
        result = Component.prototype.viewModel({}, parentViewModel)();
        expect(result.attr('useSnapshots')).toEqual(false);
      });
    });

    describe('isLoadingOrSaving() method', function () {
      beforeEach(function () {
        viewModel = new Component.prototype.viewModel({}, parentViewModel)();
      });
      it('returns true if it is saving', function () {
        viewModel.attr('is_saving', true);
        expect(viewModel.isLoadingOrSaving()).toEqual(true);
      });
      it('returns true if it is loading', function () {
        viewModel.attr('is_loading', true);
        expect(viewModel.isLoadingOrSaving()).toEqual(true);
      });
      it('returns false if page is not loading, it is not saving,' +
      ' type change is not blocked and it is not loading', function () {
        viewModel.attr('is_saving', false);
        viewModel.attr('is_loading', false);
        expect(viewModel.isLoadingOrSaving()).toEqual(false);
      });
    });

    describe('updateFreezedConfigToLatest() method', function () {
      it('sets freezedConfigTillSubmit field to currConfig', function () {
        viewModel.attr('currConfig', {
          general: {
            prop1: {},
            prop2: {},
          },
          special: [{
            types: ['Type1', 'Type2'],
            config: {},
          }],
        });

        viewModel.updateFreezedConfigToLatest();
        expect(viewModel.attr('freezedConfigTillSubmit'))
          .toBe(viewModel.attr('currConfig'));
      });
    });

    describe('onSubmit() method', function () {
      let vm;

      beforeEach(function () {
        vm = new Component.prototype.viewModel({}, parentViewModel)();
        vm.attr({
          freezedConfigTillSubmit: null,
          currConfig: {
            a: 1,
            b: 2,
          },
        });
      });

      it('sets freezedConfigTillSubmit to currConfig',
        function () {
          vm.onSubmit();

          expect(vm.attr('freezedConfigTillSubmit')).toEqual(
            vm.attr('currConfig')
          );
        });
    });
  });

  describe('map() method', function () {
    let spyObj;

    beforeEach(function () {
      viewModel.attr({
        newEntries: [],
      });
      handler = events['map'];
      spyObj = jasmine.createSpy();
    });

    it('updates freezed config to the current config', function () {
      _.assign(viewModel, {
        updateFreezedConfigToLatest:
          jasmine.createSpy('updateFreezedConfigToLatest'),
      });

      handler.call({
        viewModel: viewModel,
        mapObjects: spyObj,
      }, 'model');
      expect(viewModel.updateFreezedConfigToLatest).toHaveBeenCalled();
    });

    it('adds model to newEntries', function () {
      viewModel.attr('newEntries', []);
      handler.call({
        viewModel: viewModel,
        mapObjects: spyObj,
      }, 'model');
      expect(viewModel.attr('newEntries').length).toEqual(1);
      expect(viewModel.attr('newEntries')[0]).toEqual('model');
    });

    it('calls mapObjects to map results', function () {
      handler.call({
        viewModel: viewModel,
        mapObjects: spyObj,
      }, 'model');
      expect(spyObj).toHaveBeenCalledWith(viewModel.attr('newEntries'));
    });
  });

  describe('".create-control click" event', function () {
    let element = {};

    beforeEach(function () {
      viewModel.attr({});
      handler = events['.create-control click'];
      element.trigger = jasmine.createSpy();
    });

    it('sets empty array to newEntries', function () {
      handler.call({viewModel: viewModel, element: element});
      expect(viewModel.attr('newEntries').length)
        .toEqual(0);
    });

    it('triggers "hideModal" event', function () {
      handler.call({viewModel: viewModel, element: element});
      expect(element.trigger).toHaveBeenCalledWith('hideModal');
    });
  });

  describe('".create-control modal:added" event', function () {
    beforeEach(function () {
      viewModel.attr({newEntries: []});
      handler = events['.create-control modal:added'];
    });

    it('adds model to newEntries', function () {
      handler.call({viewModel: viewModel}, {}, {}, 'model');
      expect(viewModel.attr('newEntries').length).toEqual(1);
      expect(viewModel.attr('newEntries')[0]).toEqual('model');
    });
  });

  describe('"{window} modal:dismiss" event', function () {
    let options;
    let spyObj;
    let element = {};

    beforeEach(function () {
      viewModel.attr({
        join_object_id: 123,
        newEntries: [1],
      });
      handler = events['{window} modal:dismiss'];
      spyObj = jasmine.createSpy();
      element.trigger = jasmine.createSpy();
    });

    it('calls mapObjects from mapper-results' +
    'if there are newEntries and ids are equal', function () {
      options = {
        uniqueId: 123,
      };
      handler.call({
        viewModel: viewModel,
        mapObjects: spyObj,
      }, {}, {}, options);
      expect(spyObj).toHaveBeenCalled();
    });

    it('does not call mapObjects from mapper-results' +
      'if there are newEntries and ids are not equal', function () {
      options = {
        uniqueId: 321,
      };
      handler.call({
        viewModel: viewModel,
        mapObjects: spyObj,
        element: element,
      }, {}, {}, options);
      expect(spyObj).not.toHaveBeenCalled();
    });

    it('triggers "showModel event"' +
      'if there are newEntries and ids are not equal', function () {
      options = {
        uniqueId: 321,
      };
      handler.call({
        viewModel: viewModel,
        mapObjects: spyObj,
        element: element,
      }, {}, {}, options);
      expect(element.trigger).toHaveBeenCalledWith('showModal');
    });

    it('does not calls mapObjects from mapper-results' +
    'if there are no newEntries', function () {
      viewModel.attr('newEntries', []);
      options = {
        uniqueId: 123,
      };
      handler.call({
        viewModel: viewModel,
        mapObjects: spyObj,
        element: element,
      }, {}, {}, options);
      expect(spyObj).not.toHaveBeenCalled();
    });

    it('triggers "showModal"' +
    'if there are no newEntries', function () {
      viewModel.attr('newEntries', []);
      options = {
        uniqueId: 123,
      };
      handler.call({
        viewModel: viewModel,
        mapObjects: spyObj,
        element: element,
      }, {}, {}, options);
      expect(element.trigger).toHaveBeenCalledWith('showModal');
    });
  });

  describe('"inserted" event', function () {
    let that;

    beforeEach(function () {
      viewModel.attr({
        selected: [1, 2, 3],
        entries: [3, 2, 1],
        onSubmit: function () {},
      });
      that = {
        viewModel: viewModel,
      };
      handler = events.inserted;
    });

    it('sets empty array to selected', function () {
      handler.call(that);
      expect(viewModel.attr('selected').length)
        .toEqual(0);
    });
    it('sets empty array to entries', function () {
      handler.call(that);
      expect(viewModel.attr('entries').length)
        .toEqual(0);
    });
  });

  describe('"closeModal" event', function () {
    let element;
    let spyObj;

    beforeEach(function () {
      viewModel.attr({});
      spyObj = {
        trigger: function () {},
      };
      element = {
        find: function () {
          return spyObj;
        },
      };
      spyOn(spyObj, 'trigger');
      handler = events.closeModal;
    });

    it('sets false to is_saving', function () {
      viewModel.attr('is_saving', true);
      handler.call({
        element: element,
        viewModel: viewModel,
      });
      expect(viewModel.attr('is_saving')).toEqual(false);
    });
    it('dismiss the modal', function () {
      handler.call({
        element: element,
        viewModel: viewModel,
      });
      expect(spyObj.trigger).toHaveBeenCalledWith('click');
    });
  });

  describe('"deferredSave" event', function () {
    let that;
    let spyObj;

    beforeEach(function () {
      spyObj = {
        trigger: function () {},
      };
      viewModel.attr({
        object: 'source',
      });
      viewModel.attr('deferred_to', {
        controller: {element: spyObj},
      });
      spyObj = viewModel.attr('deferred_to').controller.element;
      that = {
        viewModel: viewModel,
        closeModal: function () {},
      };
      spyOn(that, 'closeModal');
      spyOn(spyObj, 'trigger');
      handler = events.deferredSave;
    });

    it('calls deferredSave', function () {
      handler.call(that);
      expect(spyObj.trigger)
        .toHaveBeenCalledWith('defer:add', [
          {arr: []},
        ]);
    });
    it('calls closeModal', function () {
      handler.call(that);
      expect(that.closeModal).toHaveBeenCalled();
    });
  });

  describe('".modal-footer .btn-map click" handler', function () {
    let that;
    let event;
    let element;
    let instance;

    beforeEach(function () {
      viewModel.attr({
        type: 'type',
        object: 'Program',
        join_object_id: '123',
        selected: [],
      });
      viewModel.attr('deferred', false);

      instance = new can.Map({
        refresh: $.noop,
      });
      spyOn(Program, 'findInCacheById')
        .and.returnValue(instance);
      event = {
        preventDefault: function () {},
      };
      element = $('<div></div>');
      handler = events['.modal-footer .btn-map click'];
      that = {
        viewModel: viewModel,
        deferredSave: jasmine.createSpy().and.returnValue('deferredSave'),
        mapObjects: events.mapObjects,
      };
      spyOn(RefreshQueue.prototype, 'enqueue')
        .and.returnValue({
          trigger: jasmine.createSpy()
            .and.returnValue(can.Deferred().resolve()),
        });
      spyOn($.prototype, 'trigger');
    });

    it('does nothing if element has class "disabled"', function () {
      let result;
      element.addClass('disabled');
      result = handler.call(that, element, event);
      expect(result).toEqual(undefined);
    });

    it('calls deferredSave if it is deferred', function () {
      let result;
      viewModel.attr('deferred', true);
      result = handler.call(that, element, event);
      expect(result).toEqual('deferredSave');
    });

    it('maps selected objects', function () {
      spyOn(that, 'mapObjects');
      handler.call(that, element, event);
      expect(that.mapObjects).toHaveBeenCalled();
    });
  });

  describe('get_title() helper', function () {
    let helper;
    beforeEach(function () {
      helper = helpers.get_title;
    });

    it('returns title of parentInstance if parentInstance defined',
      function () {
        let result;
        spyOn(modelsUtils, 'getInstance').and.returnValue({
          title: 'mockTitle',
        });
        result = helper.call(viewModel);
        expect(result).toEqual('mockTitle');
      });
    it('returns object if parentInstance undefined',
      function () {
        let result;
        viewModel.attr({
          object: 'mockInstance',
          parentInstance: undefined,
        });
        result = helper.call(viewModel);
        expect(result).toEqual('mockInstance');
      });
  });

  describe('get_object() helper', function () {
    let helper;

    beforeEach(function () {
      helper = helpers.get_object;
    });

    it('returns type.title_plural if it is defined', function () {
      let result;
      viewModel.attr({
        type: 'Program',
      });
      result = helper.call(viewModel);
      expect(result).toEqual('Programs');
    });
    it('returns "Objects" if type.title_plural is null', function () {
      let result;
      viewModel.attr({
        type: null,
      });
      result = helper.call(viewModel);
      expect(result).toEqual('Objects');
    });
  });

  describe('allowedToCreate() method', function () {
    let originalVM;

    beforeAll(function () {
      originalVM = viewModel.attr();
    });

    afterAll(function () {
      viewModel.attr(originalVM);
    });

    it('returns true if it is not an in-scope model',
      function () {
        let result;
        spyOn(SnapshotUtils, 'isInScopeModel').and.returnValue(false);
        result = viewModel.allowedToCreate();
        expect(result).toEqual(true);
      });

    it('returns true if it is an in-scope model but mapped type is not ' +
    'snapshotable',
    function () {
      let result;
      spyOn(SnapshotUtils, 'isInScopeModel').and.returnValue(true);
      result = viewModel.allowedToCreate();
      expect(result).toEqual(true);
    });

    it('returns false if it is an in-scope model and mapped type is ' +
    'snapshotable',
    function () {
      let result;
      viewModel.attr('type', 'Control');
      spyOn(SnapshotUtils, 'isInScopeModel').and.returnValue(true);
      result = viewModel.allowedToCreate();
      expect(result).toEqual(false);
    });
  });

  describe('showWarning() method', function () {
    let originalVM;

    beforeAll(function () {
      originalVM = viewModel.attr();
    });

    afterAll(function () {
      viewModel.attr(originalVM);
    });

    it('returns false if is an in-scope model', function () {
      let result;
      spyOn(SnapshotUtils, 'isInScopeModel').and.returnValue(true);
      result = viewModel.showWarning();
      expect(result).toEqual(false);
    });

    it('returns true if source object is a Snapshot parent and mapped type ' +
    'is snapshotable', function () {
      let result;
      spyOn(SnapshotUtils, 'isInScopeModel').and.returnValue(false);
      viewModel.attr('object', 'Audit');
      viewModel.attr('type', 'Control');
      result = viewModel.showWarning();
      expect(result).toEqual(true);
    });

    it('returns true if mapped object is both a ' +
      'Snapshot parent and snapshotable', function () {
      let result;
      spyOn(SnapshotUtils, 'isInScopeModel').and.returnValue(false);
      spyOn(SnapshotUtils, 'isSnapshotParent').and.callFake(function (v) {
        return v === 'o';
      });
      viewModel.attr('object', 'o');
      viewModel.attr('type', 'Control');
      result = viewModel.showWarning();
      expect(result).toEqual(true);
    });
  });
});
