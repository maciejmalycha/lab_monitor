Highcharts.setOptions({
    global : {
        useUTC : false
    }
});

function rackDiagram(ctx, map, url_template, rack) {
    var racks = 7;
    var units = 42;

    var width = ctx.canvas.width;
    var height = ctx.canvas.height;

    var rack_width = parseInt(width/racks);
    var unit_height = parseInt(height/units);

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
        var y = parseInt(height-(server.size+server.pos)*unit_height);
        var h = server.size*unit_height;

        map.append(
            $('<area>').attr('shape', 'rect')
                .attr('coords', [x,y,x+w,y+h].join(','))
                .attr('href', url_template.replace(/_/, server.name))
                .attr('title', server.name)
        )

        // server shape
        ctx.beginPath();
        ctx.rect(x, y, w, h);
        ctx.fillStyle = '#666';
        ctx.fill();
        ctx.lineWidth = 1;
        ctx.strokeStyle = 'black';
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
        ctx.beginPath();
        ctx.font = '10px monospace';
        ctx.textAlign = 'left';
        ctx.fillStyle = '#fff';
        ctx.textBaseline = 'bottom';
        ctx.fillText(server.name, x+10, y+h);
        ctx.closePath();

        // temperature
        ctx.beginPath();
        ctx.font = '20px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#fff';
        ctx.textBaseline = 'hanging';
        ctx.fillText(server.temp+'°', x+rack_width/2, y+3);
        ctx.closePath();

    });
}

function drawChart(url, area){
    var series_data = [];
    $.getJSON(url, function(r){
        $.each(r, function(name, data){
            series_data.push({
                'name': name,
                'data': data,
                'animation': false
            });
        });

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
                inputEnabled: false
            },
            series: series_data
        })
    })
}