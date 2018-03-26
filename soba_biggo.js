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
//     var autocompleteFieldsArray = ['Gene', 'Species', 'person'];
    var autocompleteFieldsArray = ['Gene', 'person'];
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

            var sUrl = cgiUrl + "?action=autocompleteXHR&taxonFq=" + taxonFq + "&field=" + field + "&";   // ajax calls need curator and datatype
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
            forcedOAC.itemArrowToEvent.subscribe(onAutocompleteItemHighlight);
            forcedOAC.itemMouseOverEvent.subscribe(onAutocompleteItemHighlight);
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

//     var oElement = document.getElementById("pmids");
//     YAHOO.util.Event.addListener(oElement, "keyup", function() {
//         delay(function(){
// //             alert('Time elapsed!');
//             var pmidTitles = document.getElementById("pmidTitles").value;
//             var pmids      = document.getElementById("pmids").value;
//             var callbacks = {
//                 success : function (o) {                                  // Successful XHR response handler
//                     if (o.responseText !== undefined) { document.getElementById('pmidTitles').value = o.responseText; } }, };
//             pmids = convertDisplayToUrlFormat(pmids);                     // convert <newValue> to URL format by escaping characters
//             pmidTitles = convertDisplayToUrlFormat(pmidTitles);           // convert <newValue> to URL format by escaping characters
//             var sUrl = cgiUrl + "?action=pmidToTitle&pmids="+pmids+"&pmidTitles="+pmidTitles;
//                 YAHOO.util.Connect.asyncRequest('GET', sUrl, callbacks);      // Make the call to the server for term info data
//             
//         }, 1000 );
//     });

} // function setAutocompleteListeners()

function onAutocompleteItemSelect(oSelf , elItem) {          // if an item is highlighted from arrows or mouseover, populate obo
//   var match = elItem[0]._sName.match(/input_(.*)/);             // get the key and value
//   var field = match[1];
  var value = elItem[1].innerHTML;                              // get the selected value
  var url = 'http://wobr2.caltech.edu/~raymond/cgi-bin/soba_biggo.cgi?action=annotSummaryCytoscape&autocompleteValue=' + value;

//   var found = value.match(/, (.*?),/i);
//   var url = 'http://131.215.12.191/~raymond/cgi-bin/soba_biggo.cgi?action=annotSummaryCytoscape&focusTermId=' + found[1];
  window.location = url;
}

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




