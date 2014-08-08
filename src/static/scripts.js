$.fn.ajaxSubmit = function() {
    $(this).on('submit', function(e){
        e.preventDefault();
        var action = $(this).attr('action') || document.location.href;
        var method = $(this).attr('method').toUpperCase() || 'GET';
        var fields = $(this).serialize();
        var errors = $(this).find('.errors');
        var loader = $(this).find('.wait');

        loader.fadeIn('fast');
        $.ajax({
            url: action,
            type: method,
            data: fields,
            success: function(data) {
                loader.fadeOut('fast');
                if(typeof data.error!='undefined')
                {
                    var err = $('<div class="alert alert-danger">').html(data.error).hide().slideDown();
                    errors.append(err);
                    setTimeout(function(){err.slideUp()}, 3000);
                }
                else
                    window.location.reload();
        }
        });
    });
}

function rackDiagram(ctx, map, url_template, lab, racks) {
    var units = 42;

    var width = ctx.canvas.width;
    var height = ctx.canvas.height;

    var rack_width = parseInt(width/racks);
    var unit_height = parseInt(height/units);

    if(typeof lab!='undefined')
    {
        // on resize this function is called again to redraw things, 
        // but there's no need to reload the data from server,
        // that's why we'll store it here 
        ctx.lab = lab;
    }
    else if(typeof ctx.lab!='undefined')
    {
        // no new data, but the size has changed
        lab = ctx.lab;
    }
    else
    {
        // respond() has been called, but data from server is not available
        // data has not been loaded yet, but in a moment an ajax request
        // will finish and this function will be called again
        return false;
    }

    ctx.clearRect(0,0,width,height);

    map.empty();

    // grid
    for(var i=1; i<racks; i++)
    {
        ctx.beginPath();
        ctx.strokeStyle = '#bbb';
        ctx.moveTo(i*rack_width, 0);
        ctx.lineTo(i*rack_width, height);
        ctx.stroke();
        ctx.closePath();
    }
    for(var j=1; j<units; j++)
    {
        ctx.beginPath();
        ctx.strokeStyle = '#ccc';
        ctx.moveTo(0, j*unit_height);
        ctx.lineTo(width, j*unit_height);
        ctx.stroke();
        ctx.closePath();
    }

    $.each(lab, function(i, server){

        var x = parseInt(server.rack*rack_width);
        var w = rack_width;
        var y = parseInt(height-(server.size+server.position-1)*unit_height);
        var h = server.size*unit_height;

        map.append(
            $('<area>').attr('shape', 'rect')
                .attr('coords', [x,y,x+w,y+h].join(','))
                .attr('href', url_template.replace(/_/, server.addr))
                .attr('title', server.addr)
        )

        // server shape
        ctx.beginPath();
        ctx.rect(x, y, w, h);
        ctx.fillStyle = '#ccc';
        ctx.fill();
        ctx.lineWidth = 1;
        ctx.strokeStyle = '#aaa';
        ctx.stroke();
        ctx.closePath();

        // power supplies
        var powerx = x+10;
        var powerdx = (rack_width-20)/(server.power_supplies.length-1);
        $.each(server.power_supplies, function(j, power){
            ctx.beginPath();
            ctx.strokeStyle = power?'#23a127':'#ff291c';
            ctx.fillStyle = power?'#28b62c':'#ff4136';
            ctx.arc(powerx+j*powerdx, y+10, 5, 0, 2*Math.PI, false);
            ctx.fill();
            ctx.stroke();
            ctx.closePath();
        });

        // server name
        ctx.font = '12px "Source Sans Pro"';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#333';
        ctx.textBaseline = 'bottom';
        // wait! the text may be too big for current canvas size
        var text_size = ctx.measureText(server.addr);
        if(text_size.width<rack_width && h>25)
        {
            ctx.fillText(server.addr, x+rack_width/2, y+h-2);
        }

        // temperature
        ctx.font = '20px "Source Sans Pro"';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#111';
        ctx.textBaseline = 'top';
        ctx.fillText(server.temperature, x+rack_width/2, y-4);

    });
}

function drawChart(url, area, params){

    Highcharts.setOptions({
        global : {
            useUTC : false
        }
    });

    var series_data = [];
    $.getJSON(url, params, function(r){
        if(!r.bounds)
        {
            $(area).html('<div class="alert alert-info">There is no data available! Please try again later.</div>');
            return;
        }

        $.each(r.data, function(name, data){
            series_data.push({
                'name': name,
                'data': data,
                'animation': false
            });
        });

        if(!series_data.length)
        {
            // If there were no data at all, the !r.bounds condition would have already returned.
            // This situation means that selected (or default) range is empty. Therefore we need to
            // reload the chart, setting available range.
            return drawChart(url, area, {end:r.bounds[1]}); // start is automatically set to 24 hours before end
        }

        if(typeof $(area).highcharts()=='undefined')
        {
            // drawing for the first time
            $(area).highcharts('StockChart', {
                navigator : {
                    adaptToUpdatedData: false,
                    series: {'name':'Navigator', 'data':[
                        [r.bounds[0], null],
                        [r.bounds[1], null],
                    ]}
                    /*xAxis: {
                        min: r.bounds[0],
                        max: r.bounds[1]
                    }*/
                },
                rangeSelector : {
                    buttons: [{
                        type: 'hour',
                        count: 1,
                        text: '1h'
                    }, {
                        type: 'hour',
                        count: 6,
                        text: '6h'
                    }, {
                        type: 'hour',
                        count: 12,
                        text: '12h'
                    }, {
                        type: 'day',
                        count: 1,
                        text: '1d'
                    }, {
                        type: 'all',
                        text: 'All'
                    }],
                    inputEnabled: false,
                    selected: 0,
                },
                legend: {
                    enabled: true
                },
                series: series_data,
                xAxis: {
                    minTickInterval: 60000,
                    events: {
                        afterSetExtremes: function(e) {
                            var axis = $(area).highcharts().xAxis[0];
                            // the user may be navigating over the available area
                            if(e.min<axis.dataMin || e.max>axis.dataMax)
                            {
                                console.log('don\'t take it easy');
                                // when the user is using a slider, this event is being called all the time
                                // to avoid unnecessary requests, we'll wait 0.1 s before updating data
                                clearTimeout($(area).data('update-timer'));
                                $(area).data('update-timer', setTimeout(function(){
                                    console.log('reload');
                                    drawChart(url, area, {start:e.min, end:e.max});
                                }, 100));
                            }
                        }
                    }
                }
            });
        }
        else
        {
            // updating series
            $.each($(area).highcharts().series, function(i,series){
                if(series.name=='Navigator')
                    return true;
                series.setData(r.data[series.name]);
            });
            //$(area).highcharts().redraw();
        }
    }).fail(function(){
        $(area).html('<div class="alert alert-danger">Failed to load data! Please try again later.</div>');
    })
}

function modalConfirm(confirm_text, ok_button)
{
    var modal = $('<div class="modal fade">')
        .append(
            $('<div class="modal-dialog">')
                .append(
                    $('<div class="modal-content">')
                        .append(
                            $('<div class="modal-header">')
                                .append(
                                    $('<button type="button" class="close" data-dismiss="modal"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>')
                                )
                                .append(
                                    $('<h4 class="modal-title">Confirm</h4>')
                                )
                        )
                        .append(
                            $('<div class="modal-body">')
                                .html(confirm_text)
                        )
                        .append(
                            $('<div class="modal-footer">')
                                .append(
                                    $('<button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>')
                                )
                                .append(
                                    ok_button
                                )
                        )
                )
        );
        $('body').append(modal);
        ok_button.on('click', function(){
            modal.modal('hide');
        });
        modal.modal('show');
}

$(function(){
    /*
    There are two types of confirmable buttons/links.

    First one is initialized by adding data-confirm attribute
    to the tag. On click, the default event is prevented,
    the confirm box pops out and the OK button is a copy
    of the original button/link, minus data-confirm
    and with CSS classes .btn.btn-danger.

    The second type is initialized by adding data-trigger-confirm
    attribute. On click, the box pops out and clicking
    the OK button triggers "confirmed" event on the original
    button or link.

    Both listeners are attached to body, so they will work
    even if the button is created later.

    However, note that if you're creating the elements dynamically,
    the data attributes cannot be assigned by $(el).data,
    because the selectors will not work. You must use
    $(el).attr or el.dataset.
    */
    $('body').on('click', '[data-confirm]', function(e){

        e.preventDefault();
        var clone = $(this).clone()
            .removeAttr('data-confirm')
            .attr('class', 'btn btn-danger')
            .html('OK');

        var confirm_text = $(this).data('confirm');

        modalConfirm(confirm_text, clone);
        
    });

    $('body').on('click', '[data-trigger-confirm]', function(e){
        var orig = $(this);
        var ok = $('<button>')
            .attr('type', 'button')
            .attr('class', 'btn btn-danger')
            .html('OK')
            .on('click', function(){
                orig.trigger('confirmed');
            });

        var confirm_text = $(this).data('trigger-confirm');

        modalConfirm(confirm_text, ok);
        
    });
});

function update_state(state)
{
    $.fx.off = !$('#monitor-status').html().length;
    $('#monitor-status').fadeOut('fast', function(){
        $('#monitor-status').html('Monitor is '+state).fadeIn('fast');
    });
    $.fx.off = false;
    
    if(state=='off')
    {
        $('#monitor-stop, #monitor-restart').parent().addClass('disabled');
        $('#monitor-start').parent().removeClass('disabled');
    }
    else if(state=='stopping' || state=='unreachable')
    {
        $('#monitor-start, #monitor-stop, #monitor-restart').parent().addClass('disabled');
    }
    else
    {
        $('#monitor-stop, #monitor-restart').parent().removeClass('disabled');
        $('#monitor-start').parent().addClass('disabled');
    }
}


$.get('/monitor/status', function(d){
    update_state(d);
});

stream = new EventSource('/monitor/stream');
stream.onupdated = [];
stream.addEventListener('message', function(e) {
    var msg = e.data;
    update_state(msg);
    
    if(msg=='idle') // loading new data has just been finished
    {
        $.each(stream.onupdated, function(i,fx){
            fx();
        });
    }
}, false);
stream.addEventListener('error', function() {
    update_state('unreachable');
}, false);

$('#monitor-start').on('click', function(e){
    e.preventDefault()
    if($(this).parent().hasClass('disabled'))
        return;
    
    $.get('/monitor/start');
});

$('#monitor-stop').on('click', function(e){
    e.preventDefault()
    if($(this).parent().hasClass('disabled'))
        return;
    
    $.get('/monitor/stop');
});

$('#monitor-restart').on('click', function(e){
    e.preventDefault()
    if($(this).parent().hasClass('disabled'))
        return;
    
    $.get('/monitor/restart');
});