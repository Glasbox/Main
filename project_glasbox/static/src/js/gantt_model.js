/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import AbstractModel from "@web_gantt/js/gantt_model";

patch(AbstractModel.prototype, 'adds additional fields', {

    _getFields() {
        const fields = this._super.apply(this, arguments);
        if (this.modelName == 'project.task') {
            fields.push('completion_date', 'user_ids', 'user_names', 'task_delay', 'check_c_date', 'date_start', 'date_end', 'milestone', 'on_hold', 'l_end_date', 'planned_duration', 'buffer_time', 'check_delay', 'check_ahead_schedule', 'check_milestone', 'check_hold', 'check_overdue', 'check_end_or_comp_date', 'check_before_start')
        }
        return fields
    },

});
