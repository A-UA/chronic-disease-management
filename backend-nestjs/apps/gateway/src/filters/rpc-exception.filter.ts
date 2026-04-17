import { Catch, ArgumentsHost, ExceptionFilter, HttpStatus } from '@nestjs/common';
import { Response } from 'express';

interface RpcErrorPayload {
  statusCode?: number;
  status?: number;
  message?: string;
}

@Catch()
export class RpcExceptionToHttpFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();

    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let message = 'Internal server error';

    // RpcException payload directly forwarded as exception (if not wrapped)
    if (exception && typeof exception === 'object') {
      const err = exception as RpcErrorPayload;
      if (err.statusCode) {
        status = err.statusCode;
      } else if (err.status) {
        status = err.status;
      }
      
      if (err.message) {
        message = err.message;
      }
    }

    response.status(status).json({
      statusCode: status,
      message,
    });
  }
}
