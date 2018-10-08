/*
  Copyright (C) 2018 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import Component from '../cycle-task-group-object-task';
import * as WorkflowHelpers from '../../../../plugins/utils/workflow-utils';
import * as CurrentPageUtils from '../../../../plugins/utils/current-page-utils';
import * as ModelsUtils from '../../../../plugins/utils/models-utils';
import * as StubModel from '../../../../models/stub';
import {getComponentVM} from '../../../../../js_specs/spec_helpers';
import Permission from '../../../../permission';

fdescribe('cycle-task-group-object-task component', function () {
  let viewModel;

  beforeEach(function () {
    viewModel = getComponentVM(Component);
  });

  describe('isInHistory get() method', () => {
    let method;

    beforeEach(function () {
      method = viewModel.define.isInHistory.get.bind(viewModel);
      spyOn(Permission, 'is_allowed_for').and.returnValue(false);
      spyOn(StubModel, 'default');
    });

    it('returns false when there are no "update permissions for cycle, ' +
    'in which an instance is included', function (done) {
      Permission.is_allowed_for.and.returnValue(false);
      method(null, (result) => {
        expect(result).toBe(false);
        done();
      });
    });

    describe('if there are "update" rights for cycle', () => {
      beforeEach(function () {
        Permission.is_allowed_for.and.returnValue(true);
        spyOn(ModelsUtils, 'getModelInstance')
          .and.returnValue(Promise.resolve());
        viewModel.attr('instance', {
          cycle: {
            id: 1,
            type: 'Cycle',
          },
        });
        StubModel.default.and
          .returnValue(viewModel.attr('instance.cycle'));
      });

      it('then is used a stub of an instance\'s cycle to check "update" ' +
      'rights', function () {
        method();

        expect(Permission.is_allowed_for)
          .toHaveBeenCalledWith('update', viewModel.attr('instance.cycle'));
      });

      it('returns true if instance\'s cycle is in history', function (done) {
        ModelsUtils.getModelInstance.and.returnValue(Promise.resolve(
          new can.Map({is_current: false})
        ));

        method(null, (result) => {
          expect(result).toBe(true);
          done();
        });
      });

      it('returns false if instance\'s cycle is active', function (done) {
        ModelsUtils.getModelInstance.and.returnValue(Promise.resolve(
          new can.Map({is_current: true})
        ));

        method(null, (result) => {
          expect(result).toBe(false);
          done();
        });
      });
    });
  });

  describe('isEditDenied get() method', () => {
    let method;
    let fakeViewModel;

    beforeEach(function () {
      fakeViewModel = new can.Map();
      method = viewModel.define.isEditDenied.get.bind(fakeViewModel);
      spyOn(Permission, 'is_allowed_for');
    });

    describe('returns true', () => {
      it('if there are no "update "permissions for the instance', function () {
        const instance = new can.Map({});
        fakeViewModel.attr('instance', instance);
        Permission.is_allowed_for.and.returnValue(false);

        const result = method();

        expect(Permission.is_allowed_for)
          .toHaveBeenCalledWith('update', instance);
        expect(result).toBe(true);
      });

      it('if the instance is in history', function () {
        Permission.is_allowed_for.and.returnValue(true);
        fakeViewModel.attr('isInHistory', true);

        expect(method()).toBe(true);
      });
    });
  });

  describe('showWorfklowLink get() method', () => {
    let getPageType;

    beforeEach(function () {
      getPageType = spyOn(CurrentPageUtils, 'getPageType');
    });

    it('returns true if page type is not equal to "Workflow"', function () {
      getPageType.and.returnValue('NotWorkflow');
      expect(viewModel.attr('showWorkflowLink')).toBe(true);
    });

    it('returns false if page type equals to "Workflow"', function () {
      getPageType.and.returnValue('Workflow');
      expect(viewModel.attr('showWorkflowLink')).toBe(false);
    });
  });

  describe('workflowLink get() method', () => {
    it('returns link to workflow, which is relevant to instance', () => {
      const id = 1234567;
      const expectedLink = `/workflows/${id}`;

      viewModel.attr('instance', {workflow: {id}});

      expect(viewModel.attr('workflowLink')).toBe(expectedLink);
    });
  });

  describe('onStateChange() method', function () {
    let event;

    beforeEach(function () {
      event = {};
      viewModel.attr('instance', {});
      spyOn(WorkflowHelpers, 'updateStatus');
    });

    it('updates status for cycle task', function () {
      event.state = 'New State';
      viewModel.onStateChange(event);
      expect(WorkflowHelpers.updateStatus).toHaveBeenCalledWith(
        viewModel.attr('instance'),
        event.state
      );
    });
  });
});
