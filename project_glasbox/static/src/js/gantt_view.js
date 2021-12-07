odoo.define('project_glasbox.ProjectGanttView', function (require) {
'use strict';
var GanttView = require('web_gantt.GanttView');
var GanttController = require('web_gantt.GanttController');
var GanttRenderer = require('web_gantt.GanttRenderer');
var GanttModel = require('project_glasbox.ProjectGanttModel');
var GanttRow = require('web_gantt.GanttRow');

var view_registry = require('web.view_registry');


var CustomGanttRow = GanttRow.extend({

    /**
     * Prepare the gantt row slots
     *
     * @private
     */
    _prepareSlots: function () {
        const { interval, time, cellPrecisions } = this.SCALES[this.state.scale];
        const precision = this.viewInfo.activeScaleInfo.precision;
        const cellTime = cellPrecisions[precision];
        const pills = this.pills
        function getSlotStyle(cellPart, subSlotUnavailabilities, isToday) {
            function color(d) {
                if (isToday) {
                    return d ? '#f4f3ed' : '#fffaeb';
                }
                return d ? '#e9ecef; z-index: 1' : '#ffffff';
            }
            const sum = subSlotUnavailabilities.reduce((acc, d) => acc + d);
            if (!sum) {
                return '';
            }
            if (cellPart === sum) {
                return `background: ${color(1)}`;
            }
            if (cellPart === 2) {
                const [c0, c1] = subSlotUnavailabilities.map(color);
                return `background: linear-gradient(90deg, ${c0} 49%, ${c1} 50%);`
            }
            if (cellPart === 4) {
                const [c0, c1, c2, c3] = subSlotUnavailabilities.map(color);
                return `background: linear-gradient(90deg, ${c0} 24%, ${c1} 25%, ${c1} 49%, ${c2} 50%, ${c2} 74%, ${c3} 75%);`
            }
        }

        // const date_diff_indays = function(date1, date2) {
        // dt1 = new Date(date1);
        // dt2 = new Date(date2);
        // return Math.floor((Date.UTC(dt2.getFullYear(), dt2.getMonth(), dt2.getDate()) - Date.UTC(dt1.getFullYear(), dt1.getMonth(), dt1.getDate()) ) /(1000 * 60 * 60 * 24));
        // }

        for(const pill in pills){
            if (pills && pills[pill].task_delay  > 0 || pills[pill].planned_duration > 0 || pills[pill].buffer_time > 0 || pills[pill].on_hold > 0) {
                const delay = pills[pill].task_delay
                const duration = pills[pill].planned_duration
                const buffer = pills[pill].buffer_time
                const hold = pills[pill].on_hold
/*                const wd = parseInt(100/(delay+duration+buffer+hold))*/
                pills.delayWidth = delay * 100
                pills.durationWidth = duration * 100
                pills.bufferWidth = buffer * 100
                pills.holdWidth = hold * 100
            }
        }

        this.slots = [];

        // We assume that the 'slots' (dates) are naturally ordered
        // and that unavailabilties have been normalized
        // (i.e. naturally ordered and pairwise disjoint).
        // A subslot is considered unavailable (and greyed) when totally covered by
        // an unavailability.
        let index = 0;
        for (const date of this.viewInfo.slots) {
            const slotStart = date;
            const slotStop = date.clone().add(1, interval);
            // debugger;
            const isToday = date.isSame(new Date(), 'day') && this.state.scale !== 'day';
            let slotStyle = '';
            if (!this.isGroup && this.unavailabilities.slice(index).length) {
                let subSlotUnavailabilities = [];
                for (let j = 0; j < this.cellPart; j++) {
                    const subSlotStart = date.clone().add(j * cellTime, time);
                    const subSlotStop = date.clone().add((j + 1) * cellTime, time).subtract(1, 'seconds');
                    let subSlotUnavailable = 0;
                    for (let i = index; i < this.unavailabilities.length; i++) {
                        let u = this.unavailabilities[i];
                        if (subSlotStop > u.stopDate) {
                            index++;
                        } else if (u.startDate <= subSlotStart) {
                            subSlotUnavailable = 1;
                            break;
                        }
                    }
                    subSlotUnavailabilities.push(subSlotUnavailable);
                }
                slotStyle = getSlotStyle(this.cellPart, subSlotUnavailabilities, isToday);
            }

            this.slots.push({
                delay: pills.delayWidth,
                buffer: pills.bufferWidth,
                duration: pills.durationWidth,
                onhold: pills.holdWidth,
                isToday: isToday,
                style: slotStyle,
                hasButtons: !this.isGroup && !this.isTotal,
                start: slotStart,
                stop: slotStop,
                pills: [],
            });
        }
    },
    /**
     * Set the draggable and resizable jQuery properties on a pill when the user
     * enters the pill.
     *
     * This is only done at this time and not in `on_attach_callback` to
     * optimize the rendering (creating jQuery draggable and resizable for
     * potentially thousands of pills is the heaviest task).
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onPillEntered: function (ev) {
        var $pill = $(ev.currentTarget);

        this._setResizable($pill);
        if (!this.isTotal && !this.options.disableDragdrop) {
            this._setDraggable($pill);
        }
        /**
         * As we don't need to show popover of each task in 'Gantt Chart',
         * so, removed popover.
         */
        // if (!this.isGroup) {
        //     this._bindPillPopover(ev.target);
        // }
    },

    /**
     * Aggregate overlapping pills in group rows
     *
     * @private
     */
    _aggregateGroupedPills: function () {
        // this._super(...arguments);
        var self = this;
        var sortedPills = _.sortBy(_.map(this.pills, _.clone), 'startDate');
        var firstPill = sortedPills[0];
        firstPill.count = 1;

        var timeToken = this.SCALES[this.state.scale].time;
        var precision = this.viewInfo.activeScaleInfo.precision;
        var cellTime = this.SCALES[this.state.scale].cellPrecisions[precision];
        var intervals = _.reduce(this.viewInfo.slots, function (intervals, slotStart) {
            intervals.push(slotStart);
            if (precision === 'half') {
                intervals.push(slotStart.clone().add(cellTime, timeToken));
            }
            return intervals;
        }, []);

        this.pills = _.reduce(intervals, function (pills, intervalStart) {
            var intervalStop = intervalStart.clone().add(cellTime, timeToken);
            var pillsInThisInterval = _.filter(self.pills, function (pill) {
                return pill.startDate < intervalStop && pill.stopDate > intervalStart;
            });
            if (pillsInThisInterval.length) {
                var previousPill = pills[pills.length - 1];
                var isContinuous = previousPill &&
                    _.intersection(previousPill.aggregatedPills, pillsInThisInterval).length;

                if (isContinuous && previousPill.count === pillsInThisInterval.length) {
                    // Enlarge previous pill so that it spans the current slot
                    previousPill.stopDate = intervalStop;
                    previousPill.aggregatedPills = previousPill.aggregatedPills.concat(pillsInThisInterval);
                } else {
                    var newPill = {
                        id: 0,
                        count: pillsInThisInterval.length,
                        aggregatedPills: pillsInThisInterval,
                        startDate: moment.max(_.min(pillsInThisInterval, 'startDate').startDate, intervalStart),
                        stopDate: moment.min(_.max(pillsInThisInterval, 'stopDate').stopDate, intervalStop),
                    };

                    // Enrich the aggregates with consolidation data
                    if (self.consolidate && self.consolidationParams.field) {
                        newPill.consolidationValue = pillsInThisInterval.reduce(
                            function (sum, pill) {
                                if (!pill[self.consolidationParams.excludeField]) {
                                    return sum + pill[self.consolidationParams.field];
                                }
                                return sum; // Don't sum this pill if it is excluded
                            },
                            0
                        );
                        newPill.consolidationMaxValue = self.consolidationParams.maxValue;
                        newPill.consolidationExceeded = newPill.consolidationValue > newPill.consolidationMaxValue;
                    }

                    pills.push(newPill);
                }
            }
            return pills;
        }, []);

        /**
         *  As we don't need to show any decoration and pill count so we removed it.
         */

        // var maxCount = _.max(this.pills, function (pill) {
        //     return pill.count;
        // }).count;
        // var minColor = 215;
        // var maxColor = 100;
        // this.pills.forEach(function (pill) {
        //     pill.consolidated = true;
        //     if (self.consolidate && self.consolidationParams.maxValue) {
        //         pill.status = pill.consolidationExceeded ? 'danger' : 'success';
        //         pill.display_name = pill.consolidationValue;
        //     } else {
        //         var color = minColor - ((pill.count - 1) / maxCount) * (minColor - maxColor);
        //         pill.style = _.str.sprintf("background-color: rgba(%s, %s, %s, 0.6)", color, color, color);
        //         pill.display_name = pill.count;
        //     }
        // });
    },
});

var CustomGanttRenderer = GanttRenderer.extend({
    config: {
        GanttRow: CustomGanttRow
    },
});

var CustomGanttView = GanttView.extend({
    config: _.extend({}, GanttView.prototype.config, {
        Controller: GanttController,
        Renderer: CustomGanttRenderer,
        Model: GanttModel,
    }),
});

view_registry.add('project_ganttview', CustomGanttView);
return CustomGanttView;
});