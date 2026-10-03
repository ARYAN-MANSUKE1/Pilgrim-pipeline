<?php
// Run: php test_ads.php   -- checks the ad matching in "new theme/functions.php" with fake WordPress data.
// Every case must print either a real ad slot or NOTHING (nothing = no empty space on the page).

define( 'ABSPATH', 1 );
define( 'MINUTE_IN_SECONDS', 60 );
$META = array(); $TEMPLE_CITIES = array( 12 ); $CHILDREN = array( 10 => array( 12 ) );
function get_posts( $a ) { global $META; return array_map( function ( $id ) { return (object) array( 'ID' => $id ); }, array_keys( $META ) ); }
function get_post_meta( $id, $k, $s ) { global $META; return isset( $META[ $id ][ $k ] ) ? $META[ $id ][ $k ] : ''; }
function update_post_meta( $id, $k, $v ) { global $META; $META[ $id ][ $k ] = $v; }
function wp_get_post_terms( $id, $t, $a ) { global $TEMPLE_CITIES; return $TEMPLE_CITIES; }
function get_term_children( $id, $t ) { global $CHILDREN; return isset( $CHILDREN[ $id ] ) ? $CHILDREN[ $id ] : array(); }
function get_transient( $k ) { return false; }
function set_transient( $k, $v, $t ) {}
function is_singular( $t ) { return true; }
function get_the_ID() { return 99; }
function is_wp_error( $x ) { return false; }
function maybe_unserialize( $x ) { return @unserialize( $x ) ?: $x; }
function sanitize_key( $s ) { return $s; }
function sanitize_html_class( $s ) { return $s; }
function esc_url( $s ) { return $s; }
function esc_attr( $s ) { return $s; }
function wp_get_attachment_image_url( $id, $s ) { return "https://x/img$id.jpg"; }
function add_action() {}

$src = file_get_contents( __DIR__ . '/new theme/functions.php' );
$a = strpos( $src, "define( 'PDS_AD_POST_TYPE'" );
$b = strpos( $src, '/* Click tracking. */' );
eval( substr( $src, $a, $b - $a ) );

function slot( $s ) { ob_start(); pds_display_ad( $s ); return trim( ob_get_clean() ); }
function check( $name, $ok ) { echo ( $ok ? 'ok   ' : 'FAIL ' ) . $name . "\n"; if ( ! $ok ) exit( 1 ); }
$today = date( 'Y-m-d' ); $past = date( 'Y-m-d', strtotime( '-10 days' ) ); $future = date( 'Y-m-d', strtotime( '+10 days' ) );
$ad = array( 'ad_status' => 'Active', 'ad_placement' => 'temple_right', 'ad_start_date' => $past, 'ad_end_date' => $future,
	'ad_target_regions' => array( 12 ), 'ad_creative_desktop' => 5, 'ad_creative_mobile' => 6, 'ad_destination_url' => 'https://shop' );

check( 'no ads at all: prints nothing', slot( 'temple_right' ) === '' );
$META = array( 1 => $ad );
$out = slot( 'temple_right' );
check( 'running ad in its slot: shown', strpos( $out, 'pds-ad-slot' ) !== false );
check( 'phone image chosen by the browser, desktop as default', strpos( $out, 'media="(max-width: 768px)" srcset="https://x/img6.jpg"' ) && strpos( $out, 'src="https://x/img5.jpg"' ) );
check( 'other slots stay empty', slot( 'temple_left' ) === '' && slot( 'temple_top' ) === '' );
check( 'impression counted', $META[1]['_ad_impressions'] >= 1 );
$META = array( 1 => array_merge( $ad, array( 'ad_end_date' => $past, 'ad_start_date' => date( 'Y-m-d', strtotime( '-20 days' ) ) ) ) );
check( 'expired campaign: nothing', slot( 'temple_right' ) === '' );
$META = array( 1 => array_merge( $ad, array( 'ad_start_date' => $future, 'ad_end_date' => date( 'Y-m-d', strtotime( '+20 days' ) ) ) ) );
check( 'campaign not started yet: nothing', slot( 'temple_right' ) === '' );
$META = array( 1 => array_merge( $ad, array( 'ad_end_date' => $today, 'ad_start_date' => $today ) ) );
check( 'one-day campaign today: shown', slot( 'temple_right' ) !== '' );
$META = array( 1 => array_merge( $ad, array( 'ad_status' => 'paused' ) ) );
check( 'paused campaign: nothing', slot( 'temple_right' ) === '' );
$META = array( 1 => array_merge( $ad, array( 'ad_target_regions' => array( 77 ) ) ) );
check( 'different city: nothing', slot( 'temple_right' ) === '' );
$META = array( 1 => array_merge( $ad, array( 'ad_target_regions' => array( 10 ) ) ) );
check( 'targets the parent region of the temple city: shown', slot( 'temple_right' ) !== '' );
$META = array( 1 => array_merge( $ad, array( 'ad_target_regions' => array() ) ) );
check( 'no target cities set: nothing', slot( 'temple_right' ) === '' );
$META = array( 1 => array_merge( $ad, array( 'ad_creative_desktop' => '', 'ad_creative_mobile' => '' ) ) );
check( 'no image uploaded: nothing', slot( 'temple_right' ) === '' );
$META = array( 1 => array( 'campaign_status' => 'active', 'placement' => 'Temple Right', 'start_date' => date( 'Ymd', strtotime( '-1 day' ) ),
	'end_date' => date( 'd/m/Y', strtotime( '+1 day' ) ), 'target_cities' => '12', 'ad_creative' => 'https://x/old.jpg' ) );
check( 'old field names and date formats still work', strpos( slot( 'temple_right' ), 'https://x/old.jpg' ) !== false );
echo "\nall ad checks passed\n";
