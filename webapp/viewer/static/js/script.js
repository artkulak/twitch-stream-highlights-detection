$(document).ready(function(){
  $('.slider').slick({
      arrows: true,
      dots: true,
      slidesToShow: 3,
      speed: 400,
      waitForAnimate: false,
      asNavFor: ".slider_big"



  });
  $('.slider_big').slick({
      arrows: false,
      fade: true,
      asNavFor: ".slider"




  })
});
