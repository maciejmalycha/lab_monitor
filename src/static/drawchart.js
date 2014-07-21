Highcharts.setOptions({
    global : {
        useUTC : false
    }
});

function draw(url, area){
    var series_data = [];
    $.getJSON(url, function(r){
        $.each(r, function(name, data){
            series_data.push({
                'name': name,
                'data': data
            });
        });

        $(area).highcharts('StockChart', {
            rangeSelector : {
                buttons: [],
                inputEnabled: false
            },
            series: series_data
        })
    })
}