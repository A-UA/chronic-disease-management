import { Catch, ArgumentsHost, ExceptionFilter, HttpStatus } from '@nestjs/common';
import { Response } from 'express';

@Catch()
export class RpcExceptionToHttpFilter implements ExceptionFilter {
  catch(exception: any, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();

    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let message = 'Internal server error';

    // RpcException payload directly forwarded as exception (if not wrapped)
    if (exception && typeof exception === 'object') {
      if (exception.statusCode) {
        status = exception.statusCode;
      } else if (exception.status) {
        status = exception.status;
      }
      
      if (exception.message) {
        message = exception.message;
      }
    }

    response.status(status).json({
      statusCode: status,
      message,
    });
  }
}
