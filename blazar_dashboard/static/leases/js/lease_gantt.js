(function(window, horizon, $, undefined) {
  'use strict';

  function init() {
    var gantt;
    var all_tasks;
    var tasks;
    var hosts;
    var form;

    var format = '%d-%b %H:%M';
    var taskStatus = {
      'active': 'task-active',
      'pending': 'task-pending'
    };

    $.getJSON('../calendar.json')
    .done(function(resp) {
      var nodeTypesPretty = [ // preserve order so it's not random
        ['compute', 'Compute Node'],
        ['storage', 'Storage'],
        ['gpu_k80', 'GPU (K80)'],
        ['gpu_m40', 'GPU (M40)'],
        ['gpu_p100', 'GPU (P100)'],
        ['compute_ib', 'Infiniband Support'],
        ['storage_hierarchy', 'Storage Hierarchy'],
        ['fpga', 'FPGA'],
        ['lowpower_xeon', 'Low power Xeon'],
        ['atom', 'Atom'],
        ['arm64', 'ARM64'],
      ];

      all_tasks = resp.reservations.map(function(reservation, i) {
        reservation.hosts = resp.reservations.filter(
          function(r) {
            return r.id === this.id;
          },
          reservation
        ).map(function(h) { return h.hypervisor_hostname; });

        return {
          'startDate': new Date(reservation.start_date),
          'endDate': new Date(reservation.end_date),
          'taskName': reservation.hypervisor_hostname,
          'status': reservation.status,
          'data': reservation
        }
      });
      tasks = all_tasks;
      hosts = resp.compute_hosts;

      // populate node-type-chooser
      var availableNodeTypes = {};
      hosts.forEach(function(host) {
          availableNodeTypes[host.node_type] = true;
      });
      nodeTypesPretty.forEach(function(nt) {
        if (availableNodeTypes[nt[0]]) {
          $('#node-type-chooser').append(new Option(nt[1], nt[0]));
        }
      });
      $('#node-type-chooser').prop('disabled', false);

      var taskNames = $.map(resp.compute_hosts, function(host, i) {
        return host.hypervisor_hostname;
      });

      $('#blazar-gantt').empty().height(20 * taskNames.length);
      gantt = d3.gantt({
        selector: '#blazar-gantt',
        taskTypes: taskNames,
        taskStatus: taskStatus,
        tickFormat: format
      });
      gantt(tasks);

      /* set initial time range */
      setTimeDomain(gantt.timeDomain());
    })
    .fail(function() {
      $('#blazar-gantt').html('<div class="alert alert-danger">Unable to load reservations.</div>');
    });

    function setTimeDomain(timeDomain) {
      form.removeClass('time-domain-processed');
      $('#dateStart').datepicker('setDate', timeDomain[0]);
      $('#timeStartHours').val(timeDomain[0].getHours());
      $('#dateEnd').datepicker('setDate', timeDomain[1]);
      $('#timeEndHours').val(timeDomain[1].getHours());
      form.addClass('time-domain-processed');
    }

    function getTimeDomain() {
      var timeDomain = [
        $('#dateStart').datepicker('getDate'),
        $('#dateEnd').datepicker('getDate')
      ];

      timeDomain[0].setHours($('#timeStartHours').val());
      timeDomain[0].setMinutes(0);
      timeDomain[1].setHours($('#timeEndHours').val());
      timeDomain[1].setMinutes(0);

      return timeDomain;
    }

    function redraw() {
      if (gantt && tasks) {
        gantt.redraw(tasks);
      }
    }

    $(window).on('resize', redraw);

    form = $('form[name="blazar-gantt-controls"]');

    $('input[data-datepicker]', form).datepicker({
      dateFormat: 'mm/dd/yyyy'
    });

    $('#node-type-chooser').change(function() {
      var timeDomain = getTimeDomain();
      var nodeType = $('#node-type-chooser').val();

      var filteredTaskNames = hosts
        .filter(function (host) {return nodeType === '*' || nodeType === host.node_type})
        .map(function (host) {return host.hypervisor_hostname});

      tasks = all_tasks.filter(function(task) {
        return filteredTaskNames.indexOf(task.taskName) >= 0
      });

      $('#blazar-gantt').empty().height(20 * filteredTaskNames.length);
      gantt = d3.gantt({
        selector: '#blazar-gantt',
        taskTypes: filteredTaskNames,
        taskStatus: taskStatus,
        tickFormat: format,
        timeDomainStart: timeDomain[0],
        timeDomainEnd: timeDomain[1],
      });
      gantt(tasks);
    });

    $('input', form).on('change', function() {
      if (form.hasClass('time-domain-processed')) {
        var timeDomain = getTimeDomain();
        if (timeDomain[0] >= timeDomain[1]) {
          timeDomain[1] = d3.time.day.offset(timeDomain[0], +1);
          setTimeDomain(timeDomain);
        }
        gantt.timeDomain(timeDomain);
        redraw();
      }
    });

    $('.gantt-quickdays').click(function() {
      var days = $(this).data("gantt-days");
      var padFraction = 1/8; // gantt chart default is 3 hours for 1 day
      var timeDomain = [
        d3.time.day.offset(Date.now(), -days * padFraction),
        d3.time.day.offset(Date.now(), days * (1 + padFraction))
      ];
      setTimeDomain(timeDomain);
      gantt.timeDomain(timeDomain);
      redraw();
    });
  }

  horizon.addInitFunction(init);

})(window, horizon, jQuery);
