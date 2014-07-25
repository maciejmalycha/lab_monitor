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


function rackDiagram(ctx, map, url_template, rack) {
    var racks = 7;
    var units = 42;

    var width = ctx.canvas.width;
    var height = ctx.canvas.height;

    var rack_width = parseInt(width/racks);
    var unit_height = parseInt(height/units);

    if(typeof rack!='undefined')
    {
        // on resize this function is called again to redraw things, 
        // but there's no need to reload the data from server,
        // that's why we'll store it here 
        ctx.rack = rack;
    }
    else if(typeof ctx.rack!='undefined')
    {
        // no new data, but the size has changed
        rack = ctx.rack;
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

    $.each(rack, function(i, server){

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
        if(text_size.width<rack_width)
        {
            ctx.fillText(server.addr, x+rack_width/2, y+h-2);
        }

        // temperature
        ctx.font = '20px "Source Sans Pro"';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#111';
        ctx.textBaseline = 'hanging';
        ctx.fillText(server.temperature, x+rack_width/2, y);

    });
}

function drawChart(url, area){

    Highcharts.setOptions({
        global : {
            useUTC : false
        }
    });

    var series_data = [];
    $.getJSON(url, function(r){
        $.each(r, function(name, data){
            series_data.push({
                'name': name,
                'data': data,
                'animation': false
            });
        });

        if(!series_data.length)
        {
            $(area).html('<div class="alert alert-info">There is no data available! Please try again later.</div>');
            return;
        }

        if(typeof $(area).highcharts()=='undefined')
        {
            // drawing for the first time
            $(area).highcharts('StockChart', {
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
                        type: 'week',
                        count: 1,
                        text: '1w'
                    }, {
                        type: 'all',
                        text: 'All'
                    }],
                    inputEnabled: false,
                    selected: 0
                },
                legend: {
                    enabled: true
                },
                series: series_data
            });
        }
        else
        {
            // updating series
            $.each($(area).highcharts().series, function(i,series){
                series.setData(r[series.name], true);
            });
            //$(area).highcharts().redraw();
        }
    }).fail(function(){
        $(area).html('<div class="alert alert-danger">Failed to load data! Please try again later.</div>');
    })
}

$(function(){
    $('[data-confirm]').on('click', function(e){

        e.preventDefault();
        clone = $(this).clone()
            .removeData('confirm')
            .attr('class', 'btn btn-danger')
            .html('OK');

        var confirm_text = $(this).data('confirm')

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
                                        clone
                                    )
                            )
                    )
            );
        $('body').append(modal);
        modal.modal('show');
    });
});

function update_state(state)
{
    $.fx.off = !$('#controller-status').html().length;
    $('#controller-status').fadeOut('fast', function(){
        $('#controller-status').html('Controller is '+state).fadeIn('fast');
    });
    $.fx.off = false;
    
    if(state=='off')
    {
        $('#controller-stop, #controller-restart').prop('disabled', true);
        $('#controller-start').prop('disabled', false);
    }
    else if(state=='stopping' || state=='unreachable')
    {
        $('#controller-start, #controller-stop, #controller-restart').prop('disabled', true);
    }
    else
    {
        $('#controller-stop, #controller-restart').prop('disabled', false);
        $('#controller-start').prop('disabled', true);
    }
}


$.get('/controller/status', function(d){
    update_state(d);
});

stream = new EventSource('/controller/stream');
stream.onupdated = [];
stream.addEventListener('message', function(e) {
    var msg = $.parseJSON(e.data);
    if(msg.level=='STATECHANGE')
    {
        update_state(msg.message);
        
        if(msg.message=='idle') // loading new data has just been finished
        {
            $.each(stream.onupdated, function(i,fx){
                fx();
            });
        }
    }
}, false);
stream.addEventListener('error', function() {
    update_state('unreachable');
}, false);