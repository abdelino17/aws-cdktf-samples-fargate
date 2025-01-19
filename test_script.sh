ALB_FQDN=tf-lb-20250118223346384400000002-528284851.us-east-1.elb.amazonaws.com
until curl -Is --max-time 5 http://$ALB_FQDN/ping | grep "HTTP/1.1 200" >/dev/null 2>&1; do
  echo "Waiting for ALB to serve traffic..."
  sleep 5
done
printf "\nALB is now ready to serve traffic:\n"
printf "  http://$ALB_FQDN\n"
