#!/usr/bin/perl

use strict;
use JSON;
use LWP::Simple;
use Time::Piece;

# use LWP::UserAgent;
# use CGI;
# use HTML::Entities;                             # for untainting with encode_entities()
# use Tie::IxHash;                                # allow hashes ordered by item added
# use Net::Domain qw(hostname hostfqdn hostdomain);
# use URI::Encode qw(uri_encode uri_decode);
# use Storable qw(dclone);                        # copy hash of hashes
# use POSIX;

my $json = JSON->new->allow_nonref;

my $date = localtime(time + 86400)->strftime('%Y%m%d');



my $outfile = "output.txt.$date.phenotype";
open(my $out, '>', $outfile) or die "Cannot open $outfile : $!";

my $errfile = "errorfile.txt.$date.phenotype";
open(ERR, ">$errfile") or die "Cannot create $errfile : $!";

my $url = 'http://wobr2.caltech.edu:8080/solr/phenotype/select?qt=standard&indent=on&wt=json&version=2.2&fl=id&start=0&rows=100000&q=document_category:bioentity&fq=taxon:%22NCBITaxon:6239%22';
my $page_data = get $url;
my $perl_scalar = $json->decode( $page_data );
my %jsonHash = %$perl_scalar;
if ($jsonHash{'response'}{'numFound'} == 0) { print qq(no data); die; }

my $count = 0;
# print qq(ID\trAll\tnAll\teAll\tnF1\teF1\tnF2\teF2\n);
foreach my $geneHash (@{ $jsonHash{"response"}{"docs"} }) {
#   $count++; last if ($count > 2);
  my %geneHash = %$geneHash;
  my $id = $geneHash{id};
#   next unless ($id =~ m/Q8N6N2/);
  my $all_url = "http://wobr2.caltech.edu/~azurebrd/cgi-bin/soba_biggo.cgi?action=annotSummaryJson&focusTermId=$id&datatype=phenotype&radio_etgo=&rootsChosen=WBPhenotype:0000886&showControlsFlag=1&fakeRootFlag=0&filterForLcaFlag=0&filterLongestFlag=0&maxNodes=0&maxDepth=0";
  my $failCount = 0;
  my ($nodesAll, $directAll, $edgesAll) = (0, 0, 0);
  while ($nodesAll < 1 && $failCount < 10) {
    ($nodesAll, $directAll, $edgesAll) = &getNodesEdges( $all_url ); }
  $failCount = 0;
  my $f1_url = "http://wobr2.caltech.edu/~azurebrd/cgi-bin/soba_biggo.cgi?action=annotSummaryJson&focusTermId=$id&datatype=phenotype&radio_etgo=&rootsChosen=WBPhenotype:0000886&showControlsFlag=1&fakeRootFlag=0&filterForLcaFlag=1&filterLongestFlag=0&maxNodes=0&maxDepth=0";
  my ($nodesF1, $directF1, $edgesF1) = (0, 0, 0);
  while ($nodesF1 < 1 && $failCount < 10) {
    ($nodesF1, $directF1, $edgesF1) = &getNodesEdges( $f1_url ); }
  $failCount = 0;
  my $f2_url = "http://wobr2.caltech.edu/~azurebrd/cgi-bin/soba_biggo.cgi?action=annotSummaryJson&focusTermId=$id&datatype=phenotype&radio_etgo=&rootsChosen=WBPhenotype:0000886&showControlsFlag=1&fakeRootFlag=0&filterForLcaFlag=1&filterLongestFlag=1&maxNodes=0&maxDepth=0";
  my ($nodesF2, $directF2, $edgesF2) = (0, 0, 0);
  while ($nodesF2 < 1 && $failCount < 10) {
    ($nodesF2, $directF2, $edgesF2) = &getNodesEdges( $f2_url ); }
  print $out qq($id\t$directAll\t$nodesAll\t$edgesAll\t$nodesF1\t$edgesF1\t$nodesF2\t$edgesF2\n);
#   print     qq($id\t$directAll\t$nodesAll\t$edgesAll\t$nodesF1\t$edgesF1\t$nodesF2\t$edgesF2\n);
#   last if ($id =~ m/Q8N6N2/);
}

# close (OUT) or die "Cannot close $outfile : $!";
close (ERR) or die "Cannot close $errfile : $!";

sub getNodesEdges {
  my $url = shift;
  my $nodeCount = 0; my $directCount = 0; my $edgeCount = 0;
  my $page_data = get $url;
#   print qq(URL $url\n);
  if ($page_data) {
      my $perl_scalar = $json->decode( $page_data );
      my %jsonHash = %$perl_scalar;
      foreach my $node (@{ $jsonHash{"elements"}{"nodes"} }) {
        if ($$node{"data"}{"annotationDirectness"} eq 'direct') { $directCount++; }
      }
      $nodeCount = scalar( @{ $jsonHash{"elements"}{"nodes"} });
      $edgeCount = scalar( @{ $jsonHash{"elements"}{"edges"} }); }
    else { print ERR qq(url did not return data $url\n); }
  return ($nodeCount, $directCount, $edgeCount);
}

__END__

