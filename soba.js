// javascript for form at ~azurebrd/public_html/cgi-bin/forms/community_gene_description.cgi
// autocomplete (not forced) on genes and species, enter PMIDs and use those plus previous matches of pmid-title to look up new pmid titles to add to list of pmid-titles in readonly textarea.  2013 06 02

var cgiUrl = 'soba.cgi';

YAHOO.util.Event.addListener(window, "load", function() {          // on load assign listeners
    setAutocompleteListeners();                                    // add listener for gene, species, pmids
}); // YAHOO.util.Event.addListener(window, "load", function() 


function setAutocompleteListeners() {                              // add listener for gene, species, pmids
//     var autocompleteFieldsArray = ['Gene', 'Species', 'person'];
    var autocompleteFieldsArray = ['Gene'];
    for (var i = 0; i < autocompleteFieldsArray.length; i++) {     // for each field to autocomplete
        var field = autocompleteFieldsArray[i];
        settingAutocompleteListeners = function() {
            var taxons = [];
            var arrCheckbox = document.getElementsByClassName("taxon");
            for (var i = 0; arrCheckbox[i]; i++) {
              if (arrCheckbox[i].checked) {
                 taxons.push('taxon_label:"'+ arrCheckbox[i].value + '"');
              }
            } // for (i = arrCheckbox.length - 1; i > -1; i--)
            var taxonFq = taxons.join('+OR+');
//             alert(taxonFq);

            var datatypeValue = 'phenotype';
            var radioDatatypeElements = document.getElementsByName("radio_datatype");
            for (var i = 0, length = radioDatatypeElements.length; i < length; i++) {
              if (radioDatatypeElements[i].checked) {
                datatypeValue = radioDatatypeElements[i].value; } }
            var sUrl = cgiUrl + "?action=autocompleteXHR&datatype=" + datatypeValue + "&taxonFq=" + taxonFq + "&field=" + field + "&";   // ajax calls need curator and datatype
//             var sUrl = cgiUrl + "?action=autocompleteXHR&taxonFq=" + taxonFq + "&field=" + field + "&";   // ajax calls need curator and datatype
            var oDS = new YAHOO.util.XHRDataSource(sUrl);          // Use an XHRDataSource
            oDS.responseType = YAHOO.util.XHRDataSource.TYPE_TEXT; // Set the responseType
            oDS.responseSchema = {                                 // Define the schema of the delimited results
                recordDelim: "\n",
                fieldDelim: "\t"
            };
            oDS.maxCacheEntries = 5;                               // Enable caching

            var forcedOrFree = "forced";
            var inputElement = document.getElementById('input_'+field);
            var containerElement = document.getElementById(forcedOrFree + field + "Container");
            var forcedOAC = new YAHOO.widget.AutoComplete(inputElement, containerElement, oDS);
            forcedOAC.queryQuestionMark = false;                   // don't add a ? to the sUrl query since it's been built with some other values
            forcedOAC.maxResultsDisplayed = 500;
            forcedOAC.forceSelection = true;
            forcedOAC.itemSelectEvent.subscribe(onAutocompleteItemSelect);
// Don't needs this because don't need action on these, if it was necessary, would have to create functions like in the OA
//             forcedOAC.selectionEnforceEvent.subscribe(onAutocompleteSelectionEnforce);
//             forcedOAC.itemArrowToEvent.subscribe(onAutocompleteItemHighlight);
//             forcedOAC.itemMouseOverEvent.subscribe(onAutocompleteItemHighlight);
            return {
                oDS: oDS,
                forcedOAC: forcedOAC
            }
        }();
    } // for (var i = 0; i < autocompleteFieldsArray.length; i++)


    // from http://stackoverflow.com/questions/1909441/jquery-keyup-delay
    var delay = (function(){						// delay executing a function until user has stopped typing for a timeout amount
        var timer = 0;
        return function(callback, ms){
            clearTimeout (timer);
            timer = setTimeout(callback, ms);
        };
    })();

} // function setAutocompleteListeners()

function onAutocompleteItemSelect(oSelf , elItem) {          // if an item is highlighted from arrows or mouseover, populate obo
//   var match = elItem[0]._sName.match(/input_(.*)/);             // get the key and value
//   var field = match[1];
  var value = elItem[1].innerHTML;                              // get the selected value
  var datatypeValue = 'phenotype';
  var radioDatatypeElements = document.getElementsByName("radio_datatype");
  for (var i = 0, length = radioDatatypeElements.length; i < length; i++) {
    if (radioDatatypeElements[i].checked) {
      datatypeValue = radioDatatypeElements[i].value; } }
  var url = 'soba.cgi?action=annotSummaryCytoscape&filterForLcaFlag=1&filterLongestFlag=1&showControlsFlag=0&datatype=' + datatypeValue + '&autocompleteValue=' + value;
  window.location = url;
}

// function convertDisplayToUrlFormat(value) {
//     if (value !== undefined) {                                                  // if there is a display value replace stuff
//         if (value.match(/\n/)) { value = value.replace(/\n/g, " "); }           // replace linebreaks with <space>
//         if (value.match(/\+/)) { value = value.replace(/\+/g, "%2B"); }         // replace + with escaped +
//         if (value.match(/\#/)) { value = value.replace(/\#/g, "%23"); }         // replace # with escaped #
//     }
//     return value;                                                               // return value in format for URL
// } // function convertDisplayToUrlFormat(value)




