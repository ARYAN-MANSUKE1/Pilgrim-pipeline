<?php
/**
* Template Name: Single Template
*
* @package WordPress
* @subpackage Twenty_Fourteen
* @since Twenty Fourteen 1.0
*/
?>

<?php get_header(); ?>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/css/bootstrap.min.css" integrity="sha384-xOolHFLEh07PJGoPkLv1IbcEPTNtaed2xpHsD9ESMhqIYd0nLMwNLD69Npy4HI+N" crossorigin="anonymous">

<style>
	
.single.single-temple.postid-9577 .content-section img { width: 100%; }	
	section.hero .container-fluid { padding: 0px; background: #333333; }
	ul#light-slider { text-align: center; }
	.lSSlideOuter .lSPager.lSGallery img { display: block; height: 50px; max-width: 100%; border-radius: 5px; }
	ul.lSPager li { margin: 5px !important; border-radius: 5px; }
	ul.lSPager.lSGallery {  display: flex; justify-content: center; align-items: center; border-radius: 10px !important; margin-left: auto !important; margin-right: auto !important; }
	ul.lSPager.lSGallery li a { display: flex; justify-content: center; }
	li.lslide { min-height: 500px !important; }
	li.lslide img { max-height: 500px; width: auto; border-radius: 10px; }
	.tl_slide_photo_container { background-color: #000000; backdrop-filter: blur(0px); padding-top: 25px; border-radius: 15px; min-height: 590px; }
	
	.temple-feature-image img { width: 100% !important; text-align: center; }
 	.feature-img-only img { height: 500px !important; width: auto; border-radius: 10px; }
	.feature-img-only { text-align: center; padding-bottom: 25px; }
	
    .bg-feature-image { height: 600px; background-position: center; background-size: cover; background-repeat: no-repeat; margin-bottom: 15px; }
    
	section.temple-details { padding: 50px 0px 0px; background: linear-gradient(#ffebd6 50%, #ffffff); }
	section.temple-details h1, section.temple-details h3 { font-family: auto !important; text-align: center !important; }
	section.temple-details h1 { font-size: 46px; }
	section.temple-details p { font-size: 18px; }
	.t21 { text-align: center; margin-bottom: 30px; }
	.t21 span { border-bottom: 2px solid #FB8B24; font-family: auto; }
	.content-section img.aligncenter { width: 100%; }
	.content-section img { width: 50%; /* border: 2px solid #fb8b23; border-radius: 15px; */ padding: 2px; margin-top: 5px; margin-bottom: 5px; }
	.content-section li::marker { color: #fb8b23; content: ""; }
	.content-section li:before { content: "•"; font-size: 16px; font-weight: 900; color: #fb8b22; margin-right: 10px; line-height: 2em; }
	
	iframe { width: 100%; height: 350px; border: 2px solid #fb8b23 !important; border-radius: 15px; }
	.oper-street-map h5 { text-align: center; padding-top: 30px; }
	span.backtohome { text-align: center; width: 100%; display: block; padding: 15px 0px; }
	span.backtohome a { color: #9a041e; }
	span.backtohome a:hover { color: #000; text-decoration: none; }
	blockquote { padding-left: 15px; border-left: 3px solid #fb8b2375; margin-left: 15px; }
	section.temple-details .content-section { /* display: flex; */ border: 3px double #9a041e50; padding: 30px; margin-bottom: 30px; text-align: justify; box-shadow: 5px 5px 10px #9a041e50; border-radius: 15px; background: #ffffff; }
	section.temple-details .content-section ul { text-align: center !important; padding-left: 0px; font-size: 18px; }
	.banner-slider { border-radius: 15px; }
	.hero { border-radius: 15px !important; margin-bottom: 30px; }
	
	
	/* Related Post	 */
	section.related { padding: 30px 0px; }
	.related-posts { text-align: center; margin-bottom: 30px; }
	ul.related-post { display: flex; gap: 15px; margin-bottom: 0; padding-left: 0px; list-style: none; }
	li.related-items { border-radius: 15px; padding: 15px; border: 1px solid #FB8B24; background-color: #FFDDBE; text-align: center; box-shadow: 0px 0px 8px #00000050; width: 33.33%; }
	li.related-items h5 { font-weight: 600; margin: 10px 0px 10px; color: #9A031E; text-align: center; font-size: 16px; }
	li.related-items img { border-radius: 10px; box-shadow: 0px 0px 8px #00000030; border: 1px solid #FB8B24; }
	li.related-items a:hover { text-decoration: none; }
	.content-section h1, .content-section h3 { text-align: left; }
	
    @media only screen and (max-width: 600px) {
    	.bg-feature-image { height: 250px; }
		section.temple-details .content-section { padding: 15px; }
		section.temple-details h1 { font-size: 28px; }
/* 		li.lslide img { max-height: 265px !important; width: auto; } */
/* 		ul.lSPager.lSGallery { width: 100% !important; margin-top: 0px !important; } */
/* 		ul.lSPager.lSGallery { display: none; } */
		.lSSlideOuter .lSPager.lSGallery img { height: 35px; }
/* 		.tl_slide_photo_container { padding: 10px; } */
		
		.feature-img-only { padding-bottom: 10px; }
		.feature-img-only img { height: auto !important; }
		
		.content-section img { width: 100%; }
		.content-section h1 { font-size: 28px; font-weight: 600; }
		.content-section h3 { font-size: 20px; font-weight: 600; }
		
		ul.related-post { flex-wrap: wrap; }
		
		.tl_slide_photo_container { padding: 0px; min-height: auto; background: none; }
		li.lslide img { max-height: auto !important; }
		ul#light-slider { height: 325px !important; }
		.banner-slider { background: none !important; }
		
		li.related-items { width: 100%; padding: 10px; }
		li.related-items .post-feature-image { height: 200px; }
    }
</style>

<!-- <section class="hero">
	<div class="container-fluid">
		<?php $image = wp_get_attachment_image_src( get_post_thumbnail_id(), 'single-post-thumbnail' ); ?>
		<div class="banner-slider" style="background-image: url('< ?php echo $image[0]; ?>'); background-size: cover; background-position: center center; background-repeat: no-repeat; background-attachment: fixed; ">
			< ?php
				$gall = get_field('gallery');;
                if(!empty($gall)) {
					echo do_shortcode( '[lightslider_looper]' );
				} else {
					echo '<div class="tl_slide_photo_container feature-img-only">';
						echo get_the_post_thumbnail( $post_id, 'full' );
					echo '</div>';
				}
			?>
		</div>
	</div>
</section> -->

<section class="temple-details">
	<div class="container">
		<div class="content-section">
<!-- 			<div class="temple-feature-image">< ?php echo get_the_post_thumbnail( $post_id, 'full' ); ?></div> -->
			<div class="bg-feature-image" style="background-image: url('<?php echo get_the_post_thumbnail_url( $post_id, 'full' ); ?>');"></div>
			<div class="mr_lang dis_lang" style="display: block;">
<!-- 				<h2 class="t21"><span>मंदिराची माहिती</span></h2> -->
				<?php the_field('mr_translation'); ?>
<!-- 				< ?php
					$content = get_field('mr_translation');
            		echo apply_filters('mr_translation', $content);
					?> -->
			</div>
			<div class="en_lang dis_lang" style="display: none;">
<!-- 				<h2 class="t21"><span>Temple Information</span></h2> -->
<!-- 				< ?php the_field('en_translation'); ?> -->
				<?php
				// Fetch the content from the ACF WYSIWYG field
				$content = get_field('en_translation');
				echo apply_filters('en_translation', $content);
				?>
			</div>
			<div class="hi_lang dis_lang" style="display: block;">
				<?php the_field('hi_translation'); ?>
			</div>
		</div>
	</div>

	<div class="hero">
		<div class="container">
			<?php $image = wp_get_attachment_image_src( get_post_thumbnail_id(), 'single-post-thumbnail' ); ?>
			<div class="banner-slider" style="background-image: url('<?php echo $image[0]; ?>'); background-size: cover; background-position: center center; background-repeat: no-repeat; background-attachment: fixed; ">
				<?php
					$gall = get_field('gallery');;
					if(!empty($gall)) {
						echo do_shortcode( '[lightslider_looper]' );
					} else {
						echo '<div class="tl_slide_photo_container feature-img-only">';
							echo get_the_post_thumbnail( $post_id, 'full' );
						echo '</div>';
					}
				?>
			</div>
		</div>
	</div>
	
	<div class="container" style="display: table;">
		<div class="oper-street-map">
<!-- 			<h5>Location</h5> -->
			<?php the_field('google_map_ifream'); ?>
		</div>
		<span class="backtohome">
			<a class="prev-icon" href="<?php echo home_url(); ?>"><i class="fa fa-long-arrow-left" aria-hidden="true"></i> Back To Home</a>
		</span>
	</div>
</section>

<section class="related">
	<div class="container">
		<?php
		while ( have_posts() ) : the_post();
			// Get related posts
			$related_posts = get_related_custom_posts_by_taxonomy(get_the_ID(), 'city');
			// Check if there are related posts
			if ($related_posts && $related_posts->have_posts()) : ?>
				<div class="related-posts">
					<div class="mr_lang dis_lang" style="display: block;">
						<h3><?php _e('मंदिरे', 'textdomain'); ?></h3>
					</div>
					<div class="en_lang dis_lang" style="display: none;">
						<h3><?php _e('Temples', 'textdomain'); ?></h3>
					</div>
					<ul class="related-post">
						<?php while ($related_posts->have_posts()) : $related_posts->the_post(); ?>
							<li class="related-items">
								<?php echo '<a href="'.get_permalink().'">' ?>
									<div class="post-feature-image" style="background-image: url('<?php echo get_the_post_thumbnail_url(); ?>');"></div>
										<div class="mr_lang dis_lang" style="display: block;">
											<h5><?php the_field('marathi_title'); ?></h5>
											<?php echo '<span class="view-details-btn"> अधिक माहिती </span>'; ?>
										</div>
										<div class="en_lang dis_lang" style="display: none;">
											<?php echo '<h5>' .get_the_title(). '</h5>' ;?>
											<?php echo '<span class="view-details-btn"> View Details </span>'; ?>
										</div>
		<!-- 								<div class="hi_lang dis_lang" style="display: none;">
											<h5>जुहू चौपाटी</h5>
										</div> -->
									<?php echo the_excerpt(); ?>
								<?php echo '</a>'; ?>
							</li>
						<?php endwhile; ?>
					</ul>
				</div>
				<?php wp_reset_postdata();		// Restore original Post Data
			endif;
		endwhile;
		?>
	</div>
</section>

<!-- <script src="https://cdn.jsdelivr.net/npm/jquery@3.5.1/dist/jquery.slim.min.js" integrity="sha384-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38MVBnE+IbbVYUew+OrCXaRkfj" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/js/bootstrap.bundle.min.js" integrity="sha384-Fy6S3B9q64WdZWQUiU+q4/2Lc9npb8tCaSX9FK7E8HnRr0Jz8D6OP9dO5Vg3Q9ct" crossorigin="anonymous"></script> -->

<?php get_footer(); ?>