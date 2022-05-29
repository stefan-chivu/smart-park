<?php

$target_dir = "uploads/";
$datum = mktime(date('H')+0, date('i'), date('s'), date('m'), date('d'), date('y'));
$target_file = $target_dir . date('Y.m.d_H:i:s_', $datum) . basename($_FILES["imageFile"]["name"]);
$uploadOk = 1;
$imageFileType = strtolower(pathinfo($target_file,PATHINFO_EXTENSION));

$sensorID = $_POST["sensorID"];
$occupied = $_POST["occupied"];

echo "\nParams:\nSensor ID: $sensorID ;\nSpot state: $occupied ;\nTarget file: $target_file\n";

// Check if image file is a actual image or fake image
if(isset($_POST["submit"])) {
  $check = getimagesize($_FILES["imageFile"]["tmp_name"]);
  if($check !== false) {
    echo "File is an image - " . $check["mime"] . ".";
    $uploadOk = 1;
  }
  else {
    echo "File is not an image.\n";
    $uploadOk = 0;
  }
}

// Check if file already exists
if (file_exists($target_file)) {
  echo "Sorry, file already exists.\n";
  $uploadOk = 0;
}

// Check file size
if ($_FILES["imageFile"]["size"] > 500000) {
  echo "Sorry, your file is too large.\n";
  $uploadOk = 0;
}

// Allow certain file formats
if($imageFileType != "jpg" && $imageFileType != "png" && $imageFileType != "jpeg"
&& $imageFileType != "gif" ) {
  echo "Sorry, only JPG, JPEG, PNG & GIF files are allowed.\n";
  $uploadOk = 0;
}

// Check if $uploadOk is set to 0 by an error
if ($uploadOk == 0) {
  echo "Sorry, your file was not uploaded.\n";
// if everything is ok, try to upload file
}
else {
  // Upload the received file to the path at $target_file
  if (move_uploaded_file($_FILES["imageFile"]["tmp_name"], $target_file)) {
    echo "The file ". basename( $_FILES["imageFile"]["name"]). " has been uploaded.\n";
    echo "\nStarting image processing for the uploaded file\n";
    
    // Call the python script for image processing and save the response in $message
    $message = exec("python3 /var/www/html/python/update_db.py $sensorID $occupied $target_file 2>&1");
    echo "\nOUTPUT:\n";
    $output = print_r($message, true);
    echo "$output";
    $outputLower = strtolower($output);
    $error_msg   = 'error';
    $pos = strpos($outputLower, $error_msg);

    if ($pos === false) {
      echo "\nNo errors uploading the file";
    } else {
        echo "\nAn error occured after uploading the file.";

    }
    
  }
  else {
    echo "Sorry, there was an error uploading your file.\n";
  }
}
?>
