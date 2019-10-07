'use strict';

var pageViewModel = {
  // Page display state vars
  pageTemplate: ko.observable('index'),
  pageContext: ko.observable(),
  activePanel: ko.observable(),
  // Specific data loaded from API to build template content
  searchResults: ko.observableArray(),
  personResults: ko.observable(),
  yearEvents: ko.observable(),
  // Generic data loaded at all times
  raceDisciplines: ko.observableArray(),
  eventYears: ko.observableArray(),
  // UI hacks
  searchSubmit: function(form){
    page('/search?' + $(form).serialize());
  },
  setActivePanel: function(tabData, element){
    var findFunc = function(){return false};
    var $root = this;
    switch($root.pageTemplate()) {
      case 'person':
        findFunc = function(){
          if (this.results.length > 0){
            $root.activePanel(this);
            return false;
          }
        }
        break;
    }
    $.each(tabData, findFunc);
  }
};

function switchPage(context, next){
  console.log('switchPage', arguments);
  $('.navbar-collapse').collapse('hide');
  pageViewModel.pageContext(context);
  pageViewModel.pageTemplate(context.pathname.split('/')[1] || 'index');
};

function doResults(context, next){
  if (context.state.results){
    pageViewModel.yearEvents(context.state.results);
    next();
  } else {
    $.get('/api/v1/events/years/' + context.params.year, function(results){
      context.state.results = results;
      context.save();
      pageViewModel.yearEvents(context.state.results);
    }).always(function(){
      next();
    });
  }
};

function doResultsYear(context, next){
    page('/results/' + pageViewModel.eventYears()[0]);
}

function doPerson(context, next){
  if (context.state.results){
    pageViewModel.searchResults(context.state.results);
    next();
  } else {
    $.get('/api/v1/results/person/' + context.params.id, function(results){
      context.state.results = results;
      context.save();
      pageViewModel.personResults(context.state.results);
    }).always(function(){
      next();
    });
  }
};

function doSearch(context, next){
  if (context.state.results){
    pageViewModel.searchResults(context.state.results);
    next();
  } else {
    $.get('/api/v1/people/' + context.querystring, params, function(results){
      context.state.results = results;
      context.save();
      pageViewModel.searchResults(context.state.results);
    }).always(function(){
      next();
    })
  }
};

window.addEventListener('load', function() {
  $.ajaxSetup({traditional: true});

  page('/', switchPage);
  page('/search*', doSearch, switchPage);
  page('/results', doResults, switchPage);
  page('/results/:year', doResultsYear, switchPage);
  page('/notifications', switchPage);
  page('/person/:id', doPerson, switchPage);
  page('/person/:id/:discipline', switchPage);
  page('/upgrades/:discipline', switchPage);
  page();

  $.get('/api/v1/discipline/', function(disciplines){
      pageViewModel.raceDisciplines(disciplines);
  });

  $.get('/api/v1/events/years/', function(years){
      pageViewModel.eventYears(years);
  });

  $.get('/html/templates.html', function(templates){
    $('body').append(templates);
    ko.options.deferUpdates = true;
    ko.applyBindings(pageViewModel);
  });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/js/serviceworker.js').then(console.log);
  }
 
});
