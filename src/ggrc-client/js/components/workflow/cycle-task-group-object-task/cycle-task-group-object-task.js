/*
  Copyright (C) 2018 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import template from './templates/cycle-task-group-object-task.mustache';
import '../../object-change-state/object-change-state';
import '../../dropdown/dropdown';
import '../../comment/comment-data-provider';
import '../../comment/comment-add-form';
import '../../comment/mapped-comments';
import {updateStatus} from '../../../plugins/utils/workflow-utils';
import {getPageType} from '../../../plugins/utils/current-page-utils';
import Permission from '../../../permission';
import Stub from '../../../models/stub';
import {getModelInstance} from '../../../plugins/utils/models-utils';

let viewModel = can.Map.extend({
  define: {
    isInHistory: {
      get(lastValue, setValue) {
        const cycleStub = new Stub(this.attr('instance.cycle'));
        let promise = Promise.resolve(false);

        /**
         * We check permissions here because current user can have
         * EDIT rights for current cycle task, but doesn't have
         * READ rights for appropriate cycle and workflow (for example,
         * the user is a Global Creator and assigned to Cycle Task) - it
         * means that he is able to edit mentioned cycle task, but cannot
         * get cycle, in which it's included.
         */
        if (Permission.is_allowed_for('update', cycleStub)) {
          promise = getModelInstance(
            cycleStub.attr('id'),
            cycleStub.attr('type'),
            'is_current'
          ).then((loadedCycle) => !loadedCycle.attr('is_current'));
        }

        promise.then(setValue);
      },
    },
    isEditDenied: {
      get() {
        return !Permission
          .is_allowed_for('update', this.attr('instance')) ||
          this.attr('isInHistory');
      },
    },
    showWorkflowLink: {
      get() {
        return getPageType() !== 'Workflow';
      },
    },
    workflowLink: {
      get() {
        return `/workflows/${this.attr('instance.workflow.id')}`;
      },
    },
  },
  instance: {},
  initialState: 'Assigned',
  onStateChange(event) {
    const instance = this.attr('instance');
    const status = event.state;
    updateStatus(instance, status);
  },
});

export default can.Component.extend({
  tag: 'cycle-task-group-object-task',
  template,
  viewModel,
});
