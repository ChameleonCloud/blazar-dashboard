(function (window, horizon, $, undefined) {
  'use strict';

  var selector = undefined;

  if ($('#blazar-calendar-flavor').length !== 0) {
    selector = '#blazar-calendar-flavor'
  }

  if (selector == undefined) return;

  var calendarElement = $(selector);
  let loaded = false
  let lastTimeDomain = undefined

  function init() {
    if (loaded) return;

    $.getJSON("resources.json")
      .done(function (resp) {
        // Populator the flavor selection dropdown
        let selector = $("#resource-type-chooser");
        selector.empty();
        resp.resources.flavors.forEach(flavor => {
          selector.append(new Option(flavor.name, flavor.id));
        });
        if (resp.resources.flavors.length > 0) {
          selector.val(resp.resources.flavors[0].id).change();
          selector.prop('disabled', false);
        }

        function maxInstances(flavorId) {
          // Max number of this flavor across all instances
          let flavor = resp.resources.flavors.find(f => f.id === flavorId);

          function passesTraits(flavor, host){
            let ret = true;
            Object.keys(flavor["extra_specs"]).forEach(key => {
              let value = flavor["extra_specs"][key];
              if (key.startsWith("trait:")) {
                let trait = key.split(":")[1];
                let hostHasTrait = host["traits"].includes(trait);
                if (value == "forbidden" && hostHasTrait) {
                  ret = false
                } else if (value == "required" && !hostHasTrait) {
                  ret = false
                }
              }
            })
            return ret;
          }

          return resp.resources.hosts.reduce(function (accumulator, host) {
            let totalVCPUs = host.vcpus;
            let totalMemory = host.memory_mb;

            if (!passesTraits(flavor, host)) {
              // Host contributes 0 to capacity if traits don't match
              totalVCPUs = 0
              totalMemory = 0;
            }

            return accumulator + Math.min(
              Math.floor(totalVCPUs / flavor.vcpus),
              Math.floor(totalMemory / flavor.ram)
            )
          }, 0)
        }

        function mergeEvents(arr) {
          // Merge requests if they have the same time. This is required for graphing
          return arr.reduce((acc, curr) => {
            if (acc.length > 0 && acc[acc.length - 1].time === curr.time) {
              let lastObj = acc[acc.length - 1];
              acc[acc.length - 1] = {
                time: lastObj.time,
                changeVCPUs: lastObj.changeVCPUs + curr.changeVCPUs,
                changeMemory: lastObj.changeMemory + curr.changeMemory,
                changeInstance: lastObj.changeInstance + curr.changeInstance,
              };
            } else {
              acc.push(curr);
            }
            return acc;
          }, []);
        }

        function calculateAvailability(flavorId) {
          // Calculate the availability over time of this flavor
          // Outline: For each host
          //   For each reservation on that host
          //     Calculate delta vcpus/memory at each reservation event {time, dMem, dVcpus}
          //     Calcualte # of instances at each event {time, # inst}
          //     Calculate delta of instances at each event {time, dInst}
          // Combine instance delta over 

          let flavor = resp.resources.flavors.find(f => f.id === flavorId);
          if (!flavor) return [];

          let instanceChangeEvents = []
          resp.resources.hosts.forEach(host => {
            // Calculate delta vcpus/memory at each reservation event
            let hostEvents = []
            resp.reservations.filter(r => r.hypervisor_hostname === host.hypervisor_hostname).forEach(reservation => {
              hostEvents.push(
                {
                  time: new Date(reservation.start_date).getTime(),
                  changeVCPUs: -reservation.usage.vcpus,
                  changeMemory: -reservation.usage.memory_mb,
                }
              );
              hostEvents.push(
                {
                  time: new Date(reservation.end_date).getTime(),
                  changeVCPUs: reservation.usage.vcpus,
                  changeMemory: reservation.usage.memory_mb
                }
              );
            });
            // We merge any allocations with same time together
            // (e.g. if someone reserves many VMs of the same flavor)
            hostEvents.sort((a, b) => a.time - b.time);
            hostEvents = mergeEvents(hostEvents)

            // We calculate available resources at each step. From this, we get # of instances, then delta of instances.

            // Running totals of resources
            let lastAvailableInstances = Math.min(
              Math.floor(host.vcpus / flavor.vcpus),
              Math.floor(host.memory_mb / flavor.ram)
            )
            let totalAvailableVCPUs = host.vcpus;
            let totalAvailableMemory = host.memory_mb;
            hostEvents.forEach(event => {
              totalAvailableVCPUs += event.changeVCPUs;
              totalAvailableMemory += event.changeMemory;

              let totalAvailableInstances = Math.min(
                Math.trunc(totalAvailableVCPUs / flavor.vcpus),
                Math.trunc(totalAvailableMemory / flavor.ram)
              )
              instanceChangeEvents.push({
                time: event.time,
                changeInstance: totalAvailableInstances - lastAvailableInstances
              })
              lastAvailableInstances = totalAvailableInstances
            })
          });
          // Merging instance numbers across time and hosts
          instanceChangeEvents.sort((a, b) => a.time - b.time);
          instanceChangeEvents = mergeEvents(instanceChangeEvents)

          let maxInstancesNumber = maxInstances(flavorId)
          // Running total of instances as we iterate over instance changes
          let availableInstancesNumber = maxInstancesNumber
          // Data to graph. We start at max instances before first allocation.
          let timeSeries = [];
          timeSeries.push({ x: 0, y: maxInstancesNumber })          
          instanceChangeEvents.forEach(event => {
            availableInstancesNumber += event.changeInstance;
            timeSeries.push({
              x: event.time, y: availableInstancesNumber
            });
          })
          // We end at max instances after all allocations.
          let lastPoint = timeSeries[timeSeries.length - 1];
          timeSeries.push({ x: lastPoint.x + 365 * 24 * 60 * 60 * 1000, y: maxInstancesNumber });

          return [{ name: "Total Availability", data: timeSeries }];
        }

        let chartOptions = {
          chart: {
            type: 'line',
            height: 600,
            toolbar: { show: false },
            zoom: { enabled: false, type: 'xy' },
          },
          stroke: {
            curve: 'stepline',
          },
          series: [],
          xaxis: {
            type: 'datetime'
          },
          yaxis: {
            title: {
              text: 'Available Instances'
            },
            min: 0,
            labels: {
              formatter: function (value) {
                return Math.trunc(value);
              }
            }
          },
          tooltip: {
            followCursor: true,
            x: {
              format: 'yyyy-MM-dd HH:mm'
            }
          },
        };

        let chart = new ApexCharts(document.querySelector("#blazar-calendar-flavor"), chartOptions);
        chart.render();

        // Update chart on flavor selection
        selector.on("change", function () {
          let selectedFlavor = $(this).val();
          let availabilityData = calculateAvailability(selectedFlavor);

          let maxInstancesNumber = maxInstances(selectedFlavor)
          chart.updateOptions({
            series: availabilityData,
            yaxis: {
              min: 0,
              max: maxInstancesNumber,
              tickAmount: Math.min(maxInstancesNumber, 20), // Cap number of labels to number of instances.
            }
          });
          if (lastTimeDomain) {
            setTimeDomain(lastTimeDomain)
          }
        });
        selector.trigger("change");


        function computeTimeDomain(days) {
          var padFraction = 1 / 8;
          return [
            d3.time.day.offset(Date.now(), -days * padFraction),
            d3.time.day.offset(Date.now(), days * (1 + padFraction))
          ];
        }
        function setTimeDomain(timeDomain) {
          lastTimeDomain = timeDomain
          form.removeClass('time-domain-processed');
          $('#dateStart').datepicker('setDate', timeDomain[0]);
          $('#timeStartHours').val(timeDomain[0].getHours());
          $('#dateEnd').datepicker('setDate', timeDomain[1]);
          $('#timeEndHours').val(timeDomain[1].getHours());
          form.addClass('time-domain-processed');
          if (chart) {
            var options = { xaxis: { min: timeDomain[0].getTime(), max: timeDomain[1].getTime() } }
            chart.updateOptions(options)
          }
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
    
        let form = $('form[name="blazar-calendar-controls"]');
        $('input[data-datepicker]', form).datepicker({
          dateFormat: 'mm/dd/yyyy'
        });

        $('input', form).on('change', function () {
          if (form.hasClass('time-domain-processed')) {
            var timeDomain = getTimeDomain();
            // If invalid ordering is chosen, set period to 1 day
            if (timeDomain[0] >= timeDomain[1]) {
              timeDomain[1] = d3.time.day.offset(timeDomain[0], +1);
            }
            setTimeDomain(timeDomain);
          }
        });

        $('.calendar-quickdays').click(function () {
          var days = parseInt($(this).data("calendar-days"));
          if (!isNaN(days)) {
            var timeDomain = computeTimeDomain(days);
            setTimeDomain(timeDomain);
          }
        });
        setTimeDomain(computeTimeDomain(7));

        loaded = true
      })
      .fail(function () {
        calendarElement.html(`<div class="alert alert-danger">${gettext("Unable to load reservations")}.</div>`);
      });
  }

  horizon.addInitFunction(init);

})(window, horizon, jQuery);
