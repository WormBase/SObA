// javascript for form at ~azurebrd/public_html/cgi-bin/forms/community_gene_description.cgi
// autocomplete (not forced) on genes and species, enter PMIDs and use those plus previous matches of pmid-title to look up new pmid titles to add to list of pmid-titles in readonly textarea.  2013 06 02

var cgiUrl = 'soba_biggo.cgi';

YAHOO.util.Event.addListener(window, "load", function() {          // on load assign listeners
    setAutocompleteListeners();                                    // add listener for gene, species, pmids
}); // YAHOO.util.Event.addListener(window, "load", function() 

// window.onscroll = function () {
// //   delay(function(){
//     var termInfoBox = document.getElementById("term_info_box");
//     var bodyTop     = window.pageYOffset;               // vertical offset of window
//     if (bodyTop > 20) {                         // scrolled more than 20
//         var setTop  = 95 - bodyTop;             // from default 95 minus the offset, move it
//         if (setTop < 20) { setTop = 20; }       // move no less than 20px from the top
//         termInfoBox.style.top = setTop + 'px';
//       }
//       else {
//         termInfoBox.style.top = '95px';         // if window not scrolled much, set to default 95px
//       }
// //   }, 5 );
// };


function setAutocompleteListeners() {                              // add listener for gene, species, pmids
    var whichPage = document.getElementById('which_page').value;

    if (whichPage === 'pickOneGenePage') {
        var field = 'Gene';
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
//             var sUrl = cgiUrl + "?action=autocompleteXHR&taxonFq=" + taxonFq + "&field=" + field + "&";   // ajax calls need curator and datatype
//             var sUrl = cgiUrl + "?action=autocompleteXHR&datatype=" + datatypeValue + "&taxonFq=" + taxonFq + "&field=Gene&";  // good until 2019 11 01
//             var sUrl = cgiUrl + "?action=autocompleteTazendraXHR&objectType=gene&";  	// to try to get from tazendra OA through cgi
            var sUrl = "https://tazendra.caltech.edu/~azurebrd/cgi-bin/forms/datatype_objects.cgi?action=autocompleteXHR&objectType=gene&";  	// to try to get from tazendra OA
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
            forcedOAC.queryDelay = 0.1;                   	   // add a delay to wait for user to stop typing
            forcedOAC.maxResultsDisplayed = 500;
            forcedOAC.forceSelection = true;
            forcedOAC.generateRequest = function(sQuery) { return "userValue=" + sQuery ; }; 	// instead of sending 'query' to form, use 'userValue'
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
    } // if (whichPage === 'pickOneGenePage')
    else if (whichPage === 'pickOneGeneBiggoPage') {
        var field = 'Gene';
        settingAutocompleteListeners = function() {
// to select from checkboxes instead of drop down
//             var taxons = [];
//             var arrCheckbox = document.getElementsByClassName("taxon");
//             for (var i = 0; arrCheckbox[i]; i++) {
//               if (arrCheckbox[i].checked) {
//                  taxons.push('taxon_label:"'+ arrCheckbox[i].value + '"'); } }
//             var taxonFq = taxons.join('+OR+');
   
            var taxonFq = '';
            if (document.getElementById("taxon_all").value === 'All') { taxonFq = ''; }
              else { taxonFq =  'taxon_label:"' + document.getElementById("taxon_all").value + '"'; }
            var datatypeValue = 'biggo';
            var sUrl = cgiUrl + "?action=autocompleteXHR&datatype=" + datatypeValue + "&taxonFq=" + taxonFq + "&field=Gene&";  // for biggo
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
            forcedOAC.queryDelay = 0.1;                   	   // add a delay to wait for user to stop typing
            forcedOAC.maxResultsDisplayed = 500;
            forcedOAC.forceSelection = true;
            forcedOAC.generateRequest = function(sQuery) { return "userValue=" + sQuery ; }; 	// instead of sending 'query' to form, use 'userValue'
            forcedOAC.itemSelectEvent.subscribe(onAutocompleteItemSelect);
            return {
                oDS: oDS,
                forcedOAC: forcedOAC
            }
        }();
    } // else if (whichPage === 'pickOneGeneBiggoPage')
    else if (whichPage === 'pickTwoGenesBiggoPage') {
        var autocompleteFieldsArray = ['One', 'Two'];
        for (var j = 0; j < autocompleteFieldsArray.length; j++) {     // for each field to autocomplete
            var fieldCount = autocompleteFieldsArray[j];
            var field = 'Gene' + fieldCount;
            settingAutocompleteListeners = function() {
// to select from checkboxes instead of drop down
//                 var taxons = [];
//                 var arrCheckbox = document.getElementsByClassName("taxon" + fieldCount);
//                 for (var i = 0; arrCheckbox[i]; i++) {
//                   if (arrCheckbox[i].checked) {
//                      taxons.push('taxon_label:"'+ arrCheckbox[i].value + '"'); } }
//                 var taxonFq = taxons.join('+OR+');
                var taxonFq = '';
                if (document.getElementById("taxon" + fieldCount).value === 'All') { taxonFq = ''; }
                  else { taxonFq =  'taxon_label:"' + document.getElementById("taxon" + fieldCount).value + '"'; }
                var datatypeValue = 'biggo';
                var sUrl = cgiUrl + "?action=autocompleteXHR&datatype=" + datatypeValue + "&taxonFq=" + taxonFq + "&field=Gene&";  // for biggo
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
                forcedOAC.queryDelay = 0.1;                   	   // add a delay to wait for user to stop typing
                forcedOAC.maxResultsDisplayed = 500;
                forcedOAC.forceSelection = true;
                forcedOAC.generateRequest = function(sQuery) { return "userValue=" + sQuery ; }; 	// instead of sending 'query' to form, use 'userValue'
                forcedOAC.itemSelectEvent.subscribe(onAutocompleteItemSelect);
                return {
                    oDS: oDS,
                    forcedOAC: forcedOAC
                }
            }();
        } // for (var j = 0; j < autocompleteFieldsArray.length; j++)      // for each field to autocomplete
    } // else if (whichPage === 'pickTwoGenesBiggoPage')
    else if (whichPage === 'pickTwoGenesPage') {
        var autocompleteFieldsArray = ['One', 'Two'];
        for (var j = 0; j < autocompleteFieldsArray.length; j++) {     // for each field to autocomplete
            var fieldCount = autocompleteFieldsArray[j];
            var field = 'Gene' + fieldCount;
            settingAutocompleteListeners = function() {
                var taxons = [];
                var arrCheckbox = document.getElementsByClassName("taxon" + fieldCount);
                for (var i = 0; arrCheckbox[i]; i++) {
                  if (arrCheckbox[i].checked) {
                     taxons.push('taxon_label:"'+ arrCheckbox[i].value + '"');
                  }
                } // for (i = arrCheckbox.length - 1; i > -1; i--)
                var taxonFq = taxons.join('+OR+');
//                 alert(taxonFq);
                var datatypeValue = 'phenotype';
                var radioDatatypeElements = document.getElementsByName("radio_datatype");
                for (var i = 0, length = radioDatatypeElements.length; i < length; i++) {
                  if (radioDatatypeElements[i].checked) {
                    datatypeValue = radioDatatypeElements[i].value; } }
//                 var sUrl = cgiUrl + "?action=autocompleteXHR&datatype=" + datatypeValue + "&taxonFq=" + taxonFq + "&field=Gene&";
//                 var sUrl = cgiUrl + "?action=autocompleteTazendraXHR&objectType=gene&";  	// to try to get from tazendra OA through cgi
                var sUrl = "https://tazendra.caltech.edu/~azurebrd/cgi-bin/forms/datatype_objects.cgi?action=autocompleteXHR&objectType=gene&";  	// to try to get from tazendra OA
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
                forcedOAC.queryDelay = 0.1;                   	   // add a delay to wait for user to stop typing
                forcedOAC.maxResultsDisplayed = 500;
                forcedOAC.forceSelection = true;
                forcedOAC.generateRequest = function(sQuery) { return "userValue=" + sQuery ; }; 	// instead of sending 'query' to form, use 'userValue'
                forcedOAC.itemSelectEvent.subscribe(onAutocompleteItemSelect);
//                 if (fieldCount === 'One') {
//                    forcedOAC.itemSelectEvent.subscribe(onAutocompleteItemSelectOne); }
//                 else if (fieldCount === 'Two') {
//                    forcedOAC.itemSelectEvent.subscribe(onAutocompleteItemSelectTwo); }
                return {
                    oDS: oDS,
                    forcedOAC: forcedOAC
                }
            }();
        } // for (var j = 0; j < autocompleteFieldsArray.length; j++)      // for each field to autocomplete
    } // else if (whichPage === 'pickTwoGenesPage')


    // from http://stackoverflow.com/questions/1909441/jquery-keyup-delay
    var delay = (function(){						// delay executing a function until user has stopped typing for a timeout amount
        var timer = 0;
        return function(callback, ms){
            clearTimeout (timer);
            timer = setTimeout(callback, ms);
        };
    })();

} // function setAutocompleteListeners()

function radioDatatypeClick(whichPage) {
  if (whichPage === 'TwoGenes') {
    validateGeneDatatype('GeneOne');
    validateGeneDatatype('GeneTwo'); }
  console.log('clicked radio');
} // function radioDatatypeClick('whichPage')

function onAutocompleteItemSelect(oSelf , elItem) {          // if an item is highlighted from arrows or mouseover, populate obo
  var match = elItem[0]._sName.match(/input_(.*)/);             // get the key and value
  var field = match[1];
  console.log('field: ' + field);
  if (field === 'Gene') {
    var value = elItem[1].innerHTML;                              // get the selected value
    var datatypeValue = 'phenotype';
    var radioDatatypeElements = document.getElementsByName("radio_datatype");
    for (var i = 0, length = radioDatatypeElements.length; i < length; i++) {
      if (radioDatatypeElements[i].checked) {
        datatypeValue = radioDatatypeElements[i].value; } }
    var url = 'soba_biggo.cgi?action=annotSummaryCytoscape&filterForLcaFlag=1&filterLongestFlag=1&showControlsFlag=0&datatype=' + datatypeValue + '&autocompleteValue=' + value;
//     window.location = url; 					// uncomment to load graph automatically
  }
  else if (field === 'GeneOne') {
    validateGeneDatatype('GeneOne');
    document.getElementById('controlsOne').style.display = 'none';
    document.getElementById('controlsTwo').style.display = ''; }
  else if (field === 'GeneTwo') {
    console.log('genetwo');
    validateGeneDatatype('GeneTwo');

// to automaticaly load graph on selection of gene two
//     var geneOneValue = document.getElementById('input_GeneOne').value;
//     var url = 'soba_biggo.cgi?action=annotSummaryCytoscape&filterForLcaFlag=1&filterLongestFlag=1&showControlsFlag=0&datatype=' + datatypeValue + '&geneOneValue=' + geneOneValue + '&autocompleteValue=' + value;
//     console.log('genetwo: ' + url);
//     window.location = url; 					// uncomment to load graph automatically
  }
} // function onAutocompleteItemSelect(oSelf , elItem) 

function validateGeneDatatype(whichGene) {
  let datatypeValue = getSelectedDatatype();
  let elMatch = document.getElementById('input_'+whichGene).value.match(/\( (.*?) \)/);
  if (elMatch !== null) {
    let geneId = 'WB:' + elMatch[1];
    console.log('geneId: ' + geneId + ' datatype: ' + datatypeValue);
    asyncCheckGeneDatatype(whichGene, geneId, datatypeValue); }
} // function validateGeneDatatype(whichGene)

function getSelectedDatatype() {
  let datatypeValue = 'phenotype';
  var radioDatatypeElements = document.getElementsByName("radio_datatype");
  for (var i = 0, length = radioDatatypeElements.length; i < length; i++) {
    if (radioDatatypeElements[i].checked) {
      datatypeValue = radioDatatypeElements[i].value; } }
  return datatypeValue;
} // function getSelectedDatatype()

function asyncCheckGeneDatatype(whichGene, geneId, datatypeValue) {
  var callbacks = {
      success : function (o) {                                  // Successful XHR response handler
          if (o.responseText !== undefined) { 
            if (o.responseText === 'no data') {
              document.getElementById('message'+whichGene).style.color = 'red';
              document.getElementById('message'+whichGene).innerHTML = o.responseText; }
            else if (o.responseText === 'has data') {
              document.getElementById('message'+whichGene).style.color = 'green';
              document.getElementById('message'+whichGene).innerHTML = o.responseText; }
            else {
              document.getElementById('message'+whichGene).style.color = 'orange';
              document.getElementById('message'+whichGene).innerHTML = 'unexpected response'; }
// console.log('SUCCESS!');
          } }, };
//   value = convertDisplayToUrlFormat(value);                     // convert <newValue> to URL format by escaping characters
//   var sUrl = cgiUrl + "?action=asyncTermInfo&field="+field+"&termid="+value;
//   let sUrl = 'http://wobr2.caltech.edu:8080/solr/' + datatypeValue + '/select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=bioentity:%22' + geneId + '%22';		// CORS does not allow this nor localhost:8080
  let sUrl = 'soba_biggo.cgi?action=validateGeneDatatype&datatype=' + datatypeValue + '&gene=' + geneId; 
console.log('send ' + sUrl);
  YAHOO.util.Connect.asyncRequest('GET', sUrl, callbacks);      // Make the call to the server for term info data
} // function function asyncTermInfo(field, value)
//     http://wobr2.caltech.edu:8080/solr/phenotype/select?qt=standard&indent=on&wt=json&version=2.2&rows=100000&fl=regulates_closure,id,annotation_class&q=document_category:annotation&fq=-qualifier:%22not%22&fq=bioentity:%22WB:WBGene00003009%22

// function asyncWbdescription(wbgene) {
//   var callbacks = {
//       success : function (o) {                                  // Successful XHR response handler
//           if (o.responseText !== undefined) {
// //             document.getElementById('wbDescription').innerHTML = o.responseText + "<br/> "; 
//             var jsonData = [];
//             try { jsonData = YAHOO.lang.JSON.parse(o.responseText); }                             // Use the JSON Utility to parse the data returned from the server
//             catch (x) { alert("JSON Parse failed!"); return; }
//             var one   = jsonData.shift();
//             var two   = jsonData.shift();
//             var three = jsonData.shift();
//             var four  = jsonData.shift();
//             var five  = jsonData.shift();
//             document.getElementById('wbDescription').value                = two;
//             document.getElementById('wbDescriptionDiv').innerHTML         = two;
//             document.getElementById('concisedescription').innerHTML       = two;
//             document.getElementById('wbDescriptionGuide').value           = three;
//             document.getElementById('wbDescriptionGuideSpan').innerHTML   = three;
//             if (four !== 'noperson') {
//               document.getElementById('contributedBy').value              = four;
//               document.getElementById('contributedByDiv').innerHTML       = four;
//               document.getElementById('contributedByGuideSpan').innerHTML = five;
//             }  else {
//               document.getElementById('contributedBy').value              = '';
//               document.getElementById('contributedByDiv').innerHTML       = '';
//               document.getElementById('contributedByGuideSpan').innerHTML = '';
//             }
// 
//           } }, };
//   wbgene = convertDisplayToUrlFormat(wbgene);                     // convert <newValue> to URL format by escaping characters
//   var sUrl = cgiUrl + "?action=asyncWbdescription&wbgene=" + wbgene + "&";
// //   alert(sUrl);
//   YAHOO.util.Connect.asyncRequest('GET', sUrl, callbacks);      // Make the call to the server for term info data
// } // function function asyncWbdescription(field, value)
// 
// 
// function onAutocompleteItemHighlight(sType, aArgs) {          // if an item is highlighted from arrows or mouseover, populate obo
// //   var value = elItem[1].innerHTML;
// //   document.getElementById('wbDescription').innerHTML = value;
//   var match = aArgs[0]._sName.match(/input_(.*)/);             // get the key and value
//   var field = match[1];
//   var myAC  = aArgs[0]; // reference back to the AC instance
//   var elLI  = aArgs[1]; // reference to the selected LI element
//   if (field === 'person') {
//     document.getElementById('term_info').parentNode.style.display   = '';
//     if (elLI.innerHTML.match(/\( (.*?) \)/) ) {                                           // match wb id in span and parenthesis
//       match       = myAC._sName.match(/input_(.*)/);
//       var field   = match[1];
//       var elMatch = elLI.innerHTML.match(/\( (.*?) \)/);
//       var wbid    = elMatch[1];
//       document.getElementById('termid_person').value = wbid;
//       asyncTermInfo(field, wbid);
//     }
//   }
// } // function onAutocompleteItemHighlight(oSelf , elItem)
// 
// function asyncTermInfo(field, value) {
//   var callbacks = {
//       success : function (o) {                                  // Successful XHR response handler
//           if (o.responseText !== undefined) { document.getElementById('term_info').innerHTML = o.responseText + "<br/> "; } }, };
//   value = convertDisplayToUrlFormat(value);                     // convert <newValue> to URL format by escaping characters
//   var sUrl = cgiUrl + "?action=asyncTermInfo&field="+field+"&termid="+value;
//   YAHOO.util.Connect.asyncRequest('GET', sUrl, callbacks);      // Make the call to the server for term info data
// } // function function asyncTermInfo(field, value)
// 
// 
// 
// function convertDisplayToUrlFormat(value) {
//     if (value !== undefined) {                                                  // if there is a display value replace stuff
//         if (value.match(/\n/)) { value = value.replace(/\n/g, " "); }           // replace linebreaks with <space>
//         if (value.match(/\+/)) { value = value.replace(/\+/g, "%2B"); }         // replace + with escaped +
//         if (value.match(/\#/)) { value = value.replace(/\#/g, "%23"); }         // replace # with escaped #
//     }
//     return value;                                                               // return value in format for URL
// } // function convertDisplayToUrlFormat(value)




